cup= 0.15
cdn = 0.15

cto1 = 50 # 50
cto2 = 19.9 # 19.9
llf23 = 30 # min 23 que provoca R_up
llf13 = 100
llf12 = 100
load_m = 50/50
Carga_m = 50 * load_m

p_fore = 50
alfa = 0.1

agc_u = 0
#########################################################
import numpy as np

usar_semilla = True

rng = np.random.default_rng(42 if usar_semilla else None)

valores = np.round(rng.uniform(-1, 1, 5), 2)
#print(valores, sum(valores))

#########################################################
import numpy as np
from scipy.stats import truncnorm

rng = np.random.default_rng(42)

# Normal truncada en [-3, 3]
a, b = -3, 3

u = truncnorm.rvs(a, b, loc=0, scale=1, size=5, random_state=rng)

# Normalizar a [-1,1]
numeros = u / 3 # u_norm

print(np.round(numeros, 2))
print("Media:", round(np.mean(numeros),5), "Std (poblacional):", 
      round(np.std(numeros),5), "Std (muestral):", round(np.std(numeros, ddof=1),5))
# numeros = round(np.mean(numeros),5)

from IPython import get_ipython

# Limpiar la consola
ipython = get_ipython()
ipython.run_line_magic('clear', '')  # limpia la consola
#from IPython import get_ipython

import warnings

warnings.filterwarnings("ignore", category = DeprecationWarning)

from gurobipy import *
from scipy.sparse import csr_matrix as sparse
from numpy import pi, array, ones, zeros, arange, ix_, r_, flatnonzero as finddiag, dot as mult
from numpy.linalg import solve, inv
import numpy as np
import pandas as pd
import time
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

import case3b_paper as mpc
sep = mpc.case3b()

t0=time.time()

Sb = sep['baseMVA']
SL = sep['SL'][0]          # slack bus

ng = len(sep['gen'])       # número de gen.
nb = len(sep['bus'])       # número de barras
nl = len(sep['branch'])    # número de líneas

#####################################################################################################################################
# Modificar Pmax gen wind (valor base: 50 MW)
#sep['gen'][1,8] = 100
# Modificar Pmax gen. 3
#sep['gen'][2,8] = 80
# Modificar vector de demanda
if 0:
    sep['bus'][2,2] = 0
    sep['bus'][1,2] = 50 

Pmax = sep['gen'][:,8]
Pmin = sep['gen'][:,9]

# Ctos. generadores
a_g = sep['gencost'][:,5]
b_g = sep['gencost'][:,6]

# Modificar ctos en gen 1 y gen 3
sep['gencost'][0,5] = cto1
sep['gencost'][2,5] = cto2

# Límite reservas
RUp = RDn = Pmax - Pmin    # límites mín./máx.

# Cto. reservas
Cto_up = np.array([1, cup, 0.7])
Cto_dn = np.array([0.25, cdn, 0.1])

Cg = sep['Cg']             # matriz de conexiones

#####################################################################################################################################
# Modificar FM línea 2 - 3 (valor base: 30 MW)
sep['branch'][2,5] = llf23
# Modificar FM línea 1 - 3 (valor base: 100 MW)
sep['branch'][1,5] = llf13
# Modificar FM línea 1 - 2 (valor base: 100 MW)
sep['branch'][0,5] = llf12

FM = sep['branch'][:,5]    # F^M
A = sep['S']               # matriz de incidencia
Bbus = sep['Bbus']         # B bus
Bf = sep['Bf']             # yA

# Carga pre contingencia
Load_bus_pre = load_m * sep['bus'][:,2]

# ENS
Cto_ens = 500
Pmax_ens = np.ones(nb) * 500 

# Parámetros salida de líneas
big_m = 1e4
sl_matrix = np.ones((nl,nl))-np.eye(nl)

# Parámetro binario de generadores que participan en AGC
vf = np.array([1, 1, 1])

contingencias = [('gen',1), ('gen',2), ('gen',3), ('line', 1), ('line', 2), ('line', 3)]
K = len(contingencias)

#####################################################################################################################################
# Parámetros escenarios de epsilon
sigma = alfa * p_fore  # desviación estándar
zeta = 3 * sigma       # límite de desviación
p_VUL = p_fore - zeta  # límite de la parte despachable

epsilon_list =  np.array([1]) * zeta #numeros * zeta #-zeta #0 #zeta 
#epsilon_list = numeros * zeta #-zeta #0 #zeta 
n_w = len(epsilon_list)

eta_list = np.array([1]) * zeta #+ epsilon_list # parte estocástica
#eta_list = zeta + epsilon_list # parte estocástica

e = 1  # generador renovable
eta_vector = np.zeros(ng)

RUp[e] = RDn[e] = p_VUL - Pmin[e] #?

#####################################################################################################################################
#####################################################################################################################################

# ==== Modelo ====
m=Model('DCOPF_3b')
m.setParam('OutputFlag', False)

# Definición de variables
# Variables de primera etapa - reserva
r_up=m.addMVar(ng, vtype=GRB.CONTINUOUS, lb=0, name='r_up')
r_dn=m.addMVar(ng, vtype=GRB.CONTINUOUS, lb=0, name='r_dn')

if agc_u == 1:
    u_up=m.addMVar(ng, vtype=GRB.BINARY, name='u_up')
    u_dn=m.addMVar(ng, vtype=GRB.BINARY, name='u_dn')

# Variables de segunda etapa
# Precontingencia
p_pre=m.addMVar((ng, n_w), vtype=GRB.CONTINUOUS, lb=0, name='Pg_pre') #lb lim inf p>=0
d_pre=m.addMVar((nb, n_w), vtype=GRB.CONTINUOUS, lb=-GRB.INFINITY, ub=GRB.INFINITY, name='d_pre')
f_pre=m.addMVar((nl, n_w), vtype=GRB.CONTINUOUS, lb=-GRB.INFINITY, ub=GRB.INFINITY, name='f_pre')
p_ens_pre=m.addMVar((nb, n_w), vtype=GRB.CONTINUOUS, lb=0, name='p_ens_pre')
m.addConstrs((p_ens_pre[i, w] == 0 for i in range(nb-1) for w in range(n_w)))

# Postcontingencia
p_post=m.addMVar((ng, K, n_w), vtype=GRB.CONTINUOUS, lb=0, name='Pg_post') 
d_post=m.addMVar((nb, K, n_w), vtype=GRB.CONTINUOUS, lb=-GRB.INFINITY, ub=GRB.INFINITY, name='d_post')
f_post=m.addMVar((nl, K, n_w), vtype=GRB.CONTINUOUS, lb=-GRB.INFINITY, ub=GRB.INFINITY, name='f_post')
p_ens_post=m.addMVar((nb, K, n_w), vtype=GRB.CONTINUOUS, lb=0, name='p_ens_post')
m.addConstrs((p_ens_post[i, k_id, w] == 0 for i in range(nb-1) for k_id in range(K) for w in range(n_w)))

#####################################################################################################################################
# ==== Función objetivo ====

Cop = LinExpr()
prob_w = 1 / n_w  # equiprobables

# Cto. pre-contingencia
Cop_pre_total = quicksum(
    a_g @ p_pre[:, w] + b_g.sum() + Cto_ens * p_ens_pre[:, w].sum()
    #Cto_ens * p_ens_pre[:, w].sum()
    for w in range(n_w)
)
# Cto. post-contingencia
Cop_post_total = quicksum(
    #(Cto_ens * p_ens_post[:, k, w].sum()) / K
    (a_g @ p_post[:, k, w] + b_g.sum() + Cto_ens * p_ens_post[:, k, w].sum()) / K
    for w in range(n_w)
    for k in range(K)
)

# Contribución del caso w a la FO total
Cop += prob_w * (Cop_pre_total + Cop_post_total)

# ==== Subject to ====

# Reserva
m.addConstr(-r_up >= -RUp * vf, name = 'RUp')
m.addConstr(-r_dn >= -RDn * vf, name = 'RDn')

if agc_u == 1:
    for i in range(ng):
        m.addConstr(-r_up[i] >= -big_m * u_dn[i])
        m.addConstr(-r_dn[i] >= -big_m * u_dn[i])

for w in range(n_w):
    eta = eta_list[w]
    eta_vector[e] = eta

    p_pre_w = p_pre[:, w]
    d_pre_w = d_pre[:, w]
    p_ens_pre_w = p_ens_pre[:, w]
    f_pre_w = f_pre[:, w]

    #####################################################################################################################################
    # ==== Precontingencia ====

    # Barra SL
    m.addConstr(d_pre[SL] == 0, f'SL_pre_w{w}')

    # Balance (LCK)
    m.addConstr(Cg @ p_pre_w + Cg @ eta_vector + p_ens_pre_w - Load_bus_pre == A.T @ f_pre_w, name = f'LCK_pre_w{w}') #Cg*Pg+P_ens-D=Bbus*d

    # Límite líneas
    m.addConstr(f_pre_w == Sb * Bf @ d_pre_w, name = f'f_pre_w{w}')
    m.addConstr(-f_pre_w >= -FM, name = f'fp_pre_w{w}')
    m.addConstr(f_pre_w >= -FM, name = f'fn_pre_w{w}')

    # Límite ángulos
    m.addConstr(-A @ d_pre_w >= -pi/2, name = f'dM_pre_w{w}')
    m.addConstr(A @ d_pre_w >= -pi/2, name = f'dm_pre_w{w}')

    # P_max y P_min
    m.addConstr(p_pre_w + eta_vector >= Pmin, name = f'P_min_pre_w{w}')
    m.addConstr(-p_pre_w - eta_vector >= -Pmax, name= f'P_max_pre_w{w}')

    # Límite P_VUL para generador renovable
    m.addConstr(-p_pre_w[e] - r_up[e] >= -p_VUL, name=f'P_VUL_e{e}_w{w}')
    #m.addConstr(p_pre_w[e] - r_dn[e] >= Pmin[e], name=f'P_min_e{e}_w{w}')

    # ENS
    m.addConstr(-p_ens_pre_w >= -Pmax_ens, name= f'P_max_ens_pre_w{w}')

    #####################################################################################################################################
    # ==== Postcontingencia ====

    for k_idx,(tipo,index) in enumerate(contingencias):
        p_post_k     = p_post[:, k_idx, w]
        d_post_k     = d_post[:, k_idx, w]
        p_ens_post_k = p_ens_post[:, k_idx, w]
        f_post_k = f_post[:, k_idx, w]
        eta_vector_post = eta_vector.copy()

        # N-1 cargas
        if tipo == 'load':
            vc_matrix = np.ones((nb,nb))-np.eye(nb)
            vc = vc_matrix[:,index-1]
            Load_bus_post_k = Load_bus_pre.copy() * vc # carga post
        
        # N-1 gen.
        elif tipo == 'gen':
            # Anular el componente estocástico para el generador fuera de servicio
            Load_bus_post_k = Load_bus_pre.copy()
            eta_vector_post[index-1] = 0
        
        # N-1 líneas
        else:
            Load_bus_post_k = Load_bus_pre.copy()

        # Barra SL
        m.addConstr(d_post_k[SL] == 0, f'SL_post[{k_idx}]_w{w}')

        # Balance (LCK)
        m.addConstr(Cg @ p_post_k + Cg @ eta_vector_post + p_ens_post_k - Load_bus_post_k == A.T @ f_post_k, name = f'LCK_post[{k_idx}]_w{w}')

        # Límite líneas
        if tipo == 'line':
            sl = sl_matrix[:,index-1]
            # m.addConstr(-f_post_k + Sb * Bf @ d_post_k >= -(1 - sl) * big_m, name = f'f_post_p[{k_idx}]_w{w}')
            # m.addConstr(f_post_k - Sb * Bf @ d_post_k >= -(1 - sl) * big_m, name = f'f_post_n[{k_idx}]_w{w}')
            # m.addConstr(-f_post_k >= -FM * sl, name = f'fp_post[{k_idx}]_w{w}')
            # m.addConstr(f_post_k >= -FM * sl, name = f'fn_post[{k_idx}]_w{w}')
            m.addConstr(f_post_k == sl * Sb * (Bf @ d_post_k), name = f'f_post[{k_idx}]_w{w}')
            m.addConstr(-f_post_k >= -FM, name = f'fp_post[{k_idx}]_w{w}')
            m.addConstr(f_post_k >= -FM, name = f'fn_post[{k_idx}]_w{w}')
            
        else:
            m.addConstr(f_post_k == Sb * Bf @ d_post_k, name = f'f_post[{k_idx}]_w{w}')
            m.addConstr(-f_post_k >= -FM, name = f'fp_post[{k_idx}]_w{w}')
            m.addConstr(f_post_k >= -FM, name = f'fn_post[{k_idx}]_w{w}')
            
        # Límite ángulos
        m.addConstr(-A @ d_post_k >= -pi/2, name = f'dM_post[{k_idx}]_w{w}')
        m.addConstr(A @ d_post_k >= -pi/2, name = f'dm_post[{k_idx}]_w{w}')

        # Generador fuera de servicio
        if tipo == 'gen':
            m.addConstr(p_post_k[index-1] == 0, f'Out_service[{k_idx}]_w{w}')
            for h in range(ng):
                if h != index-1:   # todos excepto el fuera de servicio
                    # P_max y P_min
                    m.addConstr(p_post_k[h] + eta_vector_post[h] >= Pmin[h], name=f'Pmin_post[{k_idx},{h}]_w{w}')
                    m.addConstr(-p_post_k[h] - eta_vector_post[h] >= -Pmax[h], name=f'Pmax_post[{k_idx},{h}]_w{w}')
                    # Limite p_VUL para generador renovable
                    if h == e:
                        m.addConstr(-p_post_k[h] >= -p_VUL, name=f'p_VUL_post[{k_idx},{h}]_w{w}')
                    
                    # Reserva
                    m.addConstr(p_pre_w[h] + r_up[h] >= p_post_k[h], name=f'Up[{k_idx},{h}]_w{w}')
                    m.addConstr(-p_pre_w[h] + r_dn[h] >= -p_post_k[h], name=f'Dn[{k_idx},{h}]_w{w}')
        else:
            # P_max y P_min
            m.addConstr(p_post_k + eta_vector_post >= Pmin, name = f'P_min_post[{k_idx}]_w{w}')
            m.addConstr(-p_post_k - eta_vector_post >= -Pmax, name= f'P_max_post[{k_idx}]_w{w}')
            
            # Limite p_VUL para generador renovable
            m.addConstr(-p_post_k[e] >= -p_VUL, name= f'p_vul_post[{k_idx}]_w{w}')

            # Reserva
            m.addConstr(p_pre_w + r_up >= p_post_k, name = f'Up[{k_idx}]_w{w}')
            m.addConstr(- p_pre_w + r_dn >= -p_post_k, name = f'Dn[{k_idx}]_w{w}')

        # ENS
        m.addConstr(-p_ens_post_k >= -Pmax_ens, name=f'P_max_ens_post[{k_idx}]_w{w}')

if agc_u == 1:
    C_res = u_up @ Cto_up + u_dn @ Cto_dn + r_up @ Cto_up + r_dn @ Cto_dn
else:
    C_res = r_up @ Cto_up + r_dn @ Cto_dn
    
Cop += C_res
m.setObjective(Cop, GRB.MINIMIZE)

t1=time.time()
m.optimize()
t2=time.time()

status = m.Status
if status == GRB.Status.OPTIMAL:
    print('Optimal found => status "%d"' % status)
elif status == GRB.Status.INF_OR_UNBD or \
    status == GRB.Status.INFEASIBLE  or \
    status == GRB.Status.UNBOUNDED:
    print('The model cannot be solved because it is infeasible or unbounded => status "%d"' % status)
