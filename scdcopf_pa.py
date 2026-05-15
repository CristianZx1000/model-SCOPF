from IPython import get_ipython

# Limpiar la consola
ipython = get_ipython()
ipython.run_line_magic('clear', '')  # limpia la consola
ipython.run_line_magic('reset', '-f')  # elimina todas las variables

import warnings

warnings.filterwarnings("ignore", category = DeprecationWarning)

import sys
from gurobipy import *
from scipy.sparse import csr_matrix as sparse
from numpy import pi, array, ones, zeros, arange, ix_, r_, flatnonzero as finddiag, dot as mult
from numpy.linalg import solve, inv
import numpy as np
import pandas as pd
import time
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# import case_SM_PA_V2 as mpc # sep_SM_PA_v4.pdf 
# valores_excepciones = [2, 3, 4, 6, 7]
# 1/6 --> 1/5
import case_SM_PA_V3 as mpc
# valores_excepciones = [2, 3, 6, 8, 9] # sep_SM_PA_v5.pdf

# excepciones = {x - 1 for x in valores_excepciones}

# Enlazar python con PowerFactory # llamar al sistema operativo
import os;
os.environ["PATH"]=r"D:\Program Files\DIgSILENT\PowerFactory 2021 SP2"+os.environ["PATH"]

# Importar la aplicación # tener acceso desde la ruta donde esta powerfactory
import sys
sys.path.append(r"D:\Program Files\DIgSILENT\PowerFactory 2021 SP2\Python\3.9")

# Importar la aplicación # importar el módulo que da acceso a la aplicación
import powerfactory as pf

app=pf.GetApplication()
#app.Show() # abrir pf en Modo Engine
 
# Activar el proyecto
user =app.GetCurrentUser()                # abre el usuario
project=app.ActivateProject('BD SM Punta Arenas 2023 ECF y EDAC wind') # abre el archivo pfd
#project=app.ActivateProject('BD SM Punta Arenas 2023 ECF y EDAC AGC') # abre el archivo pfd
prj = app.GetActiveProject()              # activar el proyecto

t0=time.time()

# 1: Obtener los datos de la red
scenarios_data = mpc.get_scenarios_data(app, prj)

gen_agc = scenarios_data["sistema"]["gen_agc_info"]

# 2: Construir red
network = mpc.build_network_matrices(scenarios_data, baseMVA=100.0)

# Ver todas las líneas identificadas
# for line_name, info in network["line_indices"].items():
#     print(f"{line_name}: índice={info['index']}, {info['fbus']}→{info['tbus']}, {info['name']}")

dicc_gen_agc = scenarios_data["sistema"]["dicc_gen_agc"]

dicc_gen = {name: i for i, name in enumerate(dicc_gen_agc.keys())}

ng_g = len(dicc_gen_agc)

agc_u = False

#⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡⚡
# === Modelo de la incertidumbre ===

p_fore = 3 #3.45  # pronóstico
alfa = 0.1           # factor de la desviación estándar

sigma = alfa * p_fore  # desviación estándar
zeta = 3 * sigma       # límite de desviación
p_VUL = p_fore - zeta  # límite de la parte despachable

# Parámetros escenarios de epsilon
from scipy.stats import truncnorm
rng = np.random.default_rng(42)     # semilla
# Normal truncada en [-3, 3]
a, b = -3, 3
u = truncnorm.rvs(a, b, loc=0, scale=1, size=5, random_state=rng)
# Normalizar a [-1,1]
numeros = u / 3 # u_norm

numeros = numeros[numeros <= 0.42]
print(len(numeros))

print("Media:", round(np.mean(numeros),5), "Std (poblacional):", round(np.std(numeros),5), 
      "Std (muestral):", round(np.std(numeros, ddof=1),5))
indice_fore = np.argmin(np.abs(numeros))
valor_fore = numeros[indice_fore]
print("Valor cercano al esperado", indice_fore, valor_fore)
idx_min = np.argmin(np.abs(numeros + 1))
val_min = numeros[idx_min]
print("Valor mínimo", idx_min, val_min)
idx_max = np.argmin(np.abs(numeros - 1))
val_max = numeros[idx_max]
print("Valor máximo", idx_max, val_max)

epsilon_list = numeros * zeta #-zeta #0 #zeta 
#epsilon_list =  np.array([1]) * zeta * 0 # factible si epsilon < ? / L=2 --> 0.54, L=6 --> 0.42
n_w = len(epsilon_list)

eta_list = zeta + epsilon_list     # parte estocástica
#eta_list = np.array([1]) * zeta

# ==== Modelo ====
m=Model('DCOPF_3b')
m.setParam('OutputFlag', False)

# Reservas globales
r_up_g=m.addMVar(ng_g, vtype=GRB.CONTINUOUS, lb=0, name='r_up_g')
r_dn_g=m.addMVar(ng_g, vtype=GRB.CONTINUOUS, lb=0, name='r_dn_g')

if agc_u:
    u_up_g=m.addMVar(ng_g, vtype=GRB.BINARY, name='u_up')
    u_dn_g=m.addMVar(ng_g, vtype=GRB.BINARY, name='u_dn')

#########################################################################################################

Cop = LinExpr()
Cto_up_g = np.zeros(ng_g)
Cto_dn_g = np.zeros(ng_g)

vars_list = []

# 3: Procesar cada caso
for u in range(1, 7):
    if u == 3:
        continue
    # if u != 2:
    #     continue

    # Seleccionar el escenario
    nombre_escenario = f"CASO {u}"
    escenario = prj.GetContents(nombre_escenario, 1)[0]
    escenario.Activate()

    # Calcular X equivalente con tap
    X_eq = mpc.calculate_reduced_X_trafo_7(scenarios_data, nombre_escenario)
    
    # Calcular matrices
    matrices = mpc.compute_sensitivity_matrices(network, X_eq)
    
    # Preparar datos
    data = mpc.prepare_case_data(scenarios_data, network, nombre_escenario, matrices)

    Sb = data['Sb']
    SL = data['SL']       # slack bus

    ng = data['ng']       # número de gen.
    nb = data['nb']       # número de barras
    nl = data['nl']       # número de líneas

    Pmax = data['Pmax']
    Pmin = data['Pmin']
    # Ctos. generadores
    a_g = data['a_g']
    b_g = data['b_g']
 
    # Nombre de generadores e índice de líneas
    g_names = data['g_names']
    branch_f = data['branch_f']
    branch_t = data['branch_t']

    # Límite reservas
    RUp = RDn = Pmax - Pmin         # límites mín./máx.

    # Cto. reserva
    Cto_up_g_caso = data["Cto_up_g"]
    Cto_dn_g_caso = data["Cto_dn_g"]

    idx_activos = [dicc_gen[name] for name in g_names]
    # Guardar costos en vectores globales
    for i_local, i_global in enumerate(idx_activos):
        Cto_up_g[i_global] = Cto_up_g_caso[i_local]
        Cto_dn_g[i_global] = Cto_dn_g_caso[i_local]

    Cg = data['Cg']             # matriz de conexiones

    FM = data['FM']             # F^M
    if u==1:
        print(FM)
    A = data['A']               # matriz de incidencia
    A_bar = data['A_bar']       # matriz de incidencia no orientada
    BfR = data['BfR']           # yA con pérdidas
    g = data['g']               # conductancia
    b = data['b']               # suceptancia

    # Carga pre
    Load_bus_pre = data['Load_bus_pre']
    #Load_bus_pre[2] -= 2.1 # PE CN
    # if u in {1, 4, 5}:
    #     Load_bus_pre[2] -= 2.1 # 2.55 # PE CN
    # if u == 1:
    #     print(Load_bus_pre)
    #     break
    # if u == 5:
        # Load_bus_pre[1] *= 2
        # Load_bus_pre[5] *= 2
    # Load_bus_pre = 2 * Load_bus_pre
    # Load_bus_pre[2] *= 2

    alm_2 = data['alm_2']
    alm_4 = data['alm_4']
    alm_11 = data['alm_11']
    alm_enap = data['alm_enap'] 

    # Generadores que participan en el CSF
    vf = data['vf']     # parámetro binario

    # Solo 3 unidades son eólicas en todos los casos, son los últimos tres generadores
    idx_erv = [ng-3, ng-2, ng-1]

    for kr in idx_erv:
        Pmax[kr] *= 1
    for kr in range(ng):
        if kr not in idx_erv:
            Pmax[kr] *= 1

    n_erv = len(idx_erv) # 3 gen. eólicos
    eta_vector = np.zeros(ng) # inicialización de eta: parte estocástica
    
    # Número de tramos para la linealización de las pérdidas
    L = 2

    k_coef = np.zeros((nl,L))
    for l in range(1,L+1):
        k_coef[:,l-1] = (2*l-1) * FM/(Sb*L)

    # Cond. de complementariedad    
    compl = 1

    # Cond. de adyacencia
    ady = 1  

    # ENS
    Cto_ens = 246.59
    Pmax_ens = Load_bus_pre # np.ones(nb) * 50
    if u == 1:
        print(nb)
        print(f"Número de barras: {len(Load_bus_pre)}", Load_bus_pre)
    
    contingencias = [('gen', i+1) for i in range(ng)]
    contingencias += [('load', 2), ('load', 4), ('load', 11), ('load', 15)]
    
    K = len(contingencias)

    #####################################################################################################################################
    # Definición de variables

    # Precontigencia
    
    p_pre = m.addMVar((ng, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'Pg_pre_caso{u}') #lb lim inf p>=0
    d_pre = m.addMVar((nb, n_w), vtype=GRB.CONTINUOUS, lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f'd_pre_caso{u}')
    p_ens_pre = m.addMVar((nb, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'p_ens_pre_caso{u}')
    
    # Fijar valor erv en pre
    # m.addConstrs((p_pre[kr,w] == 1.8 for kr in idx_erv for w in range(n_w)), name=f'p_pre_caso{u}_erv')

    # m.addConstrs((p_ens_pre[i,w] == 0 for i in range(nb-1) for w in range(n_w) if i not in excepciones), name=f'p_ens_pre_bus_caso{u}')

    f_pre = m.addMVar((nl, n_w), vtype=GRB.CONTINUOUS, lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f'f_pre_caso{u}')
    fp_pre = m.addMVar((nl, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'fp_pre_caso{u}')
    fn_pre = m.addMVar((nl, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'fn_pre_caso{u}')
    ploss_pre = m.addMVar((nl, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'Ploss_pre_caso{u}')
    df_pre = m.addMVar((nl, L, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'df_pre_caso{u}')
    n_lf_pre = m.addMVar((nl, n_w), vtype=GRB.BINARY, name=f'n_lf_pre_caso{u}') # Var. bin. cond. de complementariedad
    n_df_pre = m.addMVar((nl, L, n_w), vtype=GRB.BINARY, name=f'n_df_pre_caso{u}') # Var. bin. cond. de adyacencia

    # Postcontingencia

    p_post = m.addMVar((ng, K, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'Pg_post_caso{u}')
    d_post = m.addMVar((nb, K, n_w), vtype=GRB.CONTINUOUS, lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f'd_post_caso{u}')
    p_ens_post = m.addMVar((nb, K, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'p_ens_post_caso{u}')

    # m.addConstrs((p_ens_post[i,k_id,w] == 0 for i in range(nb-1) for k_id in range(K) for w in range(n_w) if i not in excepciones), name=f'p_ens_post_bus_caso{u}')
    
    f_post = m.addMVar((nl, K, n_w), vtype=GRB.CONTINUOUS, lb=-GRB.INFINITY, ub=GRB.INFINITY, name=f'f_post_caso{u}')
    fp_post = m.addMVar((nl, K, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'fp_post_caso{u}')
    fn_post = m.addMVar((nl, K, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'fn_post_caso{u}')
    ploss_post = m.addMVar((nl, K, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'Ploss_post_caso{u}')
    df_post = m.addMVar((nl, L, K, n_w), vtype=GRB.CONTINUOUS, lb=0, name=f'df_post_caso{u}')
    n_lf_post = m.addMVar((nl, K, n_w), vtype=GRB.BINARY, name=f'n_lf_post_caso{u}')
    n_df_post = m.addMVar((nl, L, K, n_w), vtype=GRB.BINARY, name=f'n_df_post_caso{u}')

    # Reserva caso u
    r_up = m.addMVar(ng, vtype=GRB.CONTINUOUS, lb=0, name=f'r_up_caso{u}')
    r_dn = m.addMVar(ng, vtype=GRB.CONTINUOUS, lb=0, name=f'r_dn_caso{u}')

    if agc_u:
        u_up = m.addMVar(ng, vtype=GRB.BINARY, name=f'u_up_caso{u}')
        u_dn = m.addMVar(ng, vtype=GRB.BINARY, name=f'u_dn_caso{u}')

    # Acoplamiento con reservas globales
    for i_local, i_global in enumerate(idx_activos):
        m.addConstr(r_up[i_local] == r_up_g[i_global])
        m.addConstr(r_dn[i_local] == r_dn_g[i_global])
        if agc_u:
            m.addConstr(u_up[i_local] == u_up_g[i_global])
            m.addConstr(u_dn[i_local] == u_dn_g[i_global])
    
    #####################################################################################################################################

    # ==== Función objetivo ====
    
    Cop_pre_total = LinExpr()
    Cop_post_total = LinExpr()

    prob_w = 1 / n_w  # equiprobables

    for w in range(n_w):
        # Precontingencia para escenario w
        Cop_pre_w = a_g @ p_pre[:, w] + p_ens_pre[:, w].sum() * Cto_ens
        #Cop_pre_w = p_ens_pre[:, w].sum() * Cto_ens
        Cop_pre_total += prob_w * Cop_pre_w
    
        # Postcontingencia para escenario w (promedio sobre todas las contingencias)
        for k in range(K):
            Cop_post_w_k = a_g @ p_post[:, k, w] + p_ens_post[:, k, w].sum() * (Cto_ens * K) #(* K)
            #Cop_post_w_k = p_ens_post[:, k, w].sum() * Cto_ens #(* K)
            Cop_post_total += prob_w * Cop_post_w_k / K

    # Contribución del caso u a la FO total
    Cop += (1/5) * (Cop_pre_total + Cop_post_total)

    vars_case = {
        'p_pre': p_pre,
        'f_pre': f_pre,
        'FM': FM,
        'ploss_pre': ploss_pre,
        'p_ens_pre': p_ens_pre,
        'p_post': p_post,
        'f_post': f_post,
        'ploss_post': ploss_post,
        'p_ens_post': p_ens_post,
        'Cop_pre': Cop_pre_total,
        'Cop_post': Cop_post_total,
        'gen_names': g_names,
        'branch_from': branch_f,
        'branch_to': branch_t,
        'contingencias': contingencias,
        'Load_bus_pre': Load_bus_pre,
        'Load_bus_post': {}
    }

    # ==== Subjet to: ====
    
    for w in range(n_w):
        eta = eta_list[w]
        for idx_w in idx_erv:
            eta_vector[idx_w] = eta

        p_pre_w = p_pre[:, w]
        d_pre_w = d_pre[:, w]
        p_ens_pre_w = p_ens_pre[:, w]
        f_pre_w = f_pre[:, w]
        fp_pre_w = fp_pre[:, w]
        fn_pre_w = fn_pre[:, w]
        ploss_pre_w = ploss_pre[:, w]
        df_pre_w = df_pre[:, :, w]
        n_lf_pre_w = n_lf_pre[:, w]
        n_df_pre_w = n_df_pre[:, :, w]

        #####################################################################################################################################
        # ==== Precontingencia ====

        # Barra SL
        m.addConstr(d_pre_w[SL] == 0, f'SL_pre_caso{u}_w{w}')

        # Balance (LCK)
        m.addConstr(Cg @ p_pre_w + Cg @ eta_vector + p_ens_pre_w - Load_bus_pre - 0.5 * A_bar.T @ ploss_pre_w == A.T @ f_pre_w, name=f'LCK_pre_caso{u}_w{w}') #Cg*Pg+P_ens-D-0.5*A^T*P_loss=A^T*f

        # Límite ángulos
        m.addConstr(-A @ d_pre_w >= -pi/2, name=f'dM_pre_caso{u}_w{w}')
        m.addConstr(A @ d_pre_w >= -pi/2, name=f'dm_pre_caso{u}_w{w}')

        # P_max y P_min
        m.addConstr(p_pre_w + eta_vector>= Pmin, name=f'P_min_pre_caso{u}_w{w}')
        m.addConstr(-p_pre_w - eta_vector>= -Pmax, name=f'P_max_pre_caso{u}_w{w}')
        #m.addConstr(p_pre_w - r_dn >= Pmin, name = f'P_min_pre_rdn_caso{u}_w{w}')
        # m.addConstr(-p_pre_w - r_up >= -Pmax, name= f'P_max_pre_rup_caso{u}_w{w}')

        # Reserva
        if not agc_u:
            m.addConstr(-r_up >= -RUp * vf, name=f'RUp_caso{u}_w{w}')
            m.addConstr(-r_dn >= -RDn * vf, name=f'RDn_caso{u}_w{w}')
        else:
            m.addConstr(-r_up >= -RUp * u_up, name=f'RUp_caso{u}_w{w}')
            m.addConstr(-r_dn >= -RDn * u_dn, name=f'RDn_caso{u}_w{w}')

        # Límite VUL
        for idx_e in idx_erv:
            m.addConstr(-p_pre_w[idx_e] - r_up[idx_e] >= -p_VUL, name = f'P_base_VUL{idx_e}_caso{u}_{w}')

        # ENS
        m.addConstr(p_ens_pre_w <= Pmax_ens, name=f'P_max_ens_pre_caso{u}_w{w}')

        #####################################################################################################################################
        # Límite y pérdidas líneas pre

        for j in range(nl):
            sum_kdf_pre = df_pre_w[j, :] @ k_coef[j, :]
            m.addConstr(ploss_pre_w[j] == (g[j]/b[j]**2) * sum_kdf_pre, name=f'f_lin_{j}_pre_caso{u}_w{w}')

        if 1-ady:
            for l in range(0,L):
                m.addConstr(-df_pre_w[:, l] >= -FM/L, name=f'df_max_pre_{l}_caso{u}_w{w}') 
                m.addConstr(df_pre_w[:, l] >= 0, name=f'df_min_pre_{l}_caso{u}_w{w}')

        m.addConstr(f_pre_w == -Sb * BfR @ d_pre_w, name = f'LVK_pre_caso{u}_w{w}')
        m.addConstr(-f_pre_w >= -FM, name = f'fmax_pre_caso{u}_w{w}')
        m.addConstr(f_pre_w >= -FM, name = f'fmin_pre_caso{u}_w{w}')

        # Sin cond. de complementariedad
        if 1-compl:
            m.addConstr(-fp_pre_w >= -FM, name = f'fp_max_pre_caso{u}_w{w}')
            m.addConstr(fp_pre_w >= 0, name = f'fp_min_pre_caso{u}_w{w}')
            m.addConstr(-fn_pre_w >= -FM, name = f'fn_max_pre_caso{u}_w{w}')
            m.addConstr(fn_pre_w >= 0, name = f'fn_min_pre_caso{u}_w{w}')
        else:
        # Con cond. de complementariedad    
            m.addConstr(-fp_pre_w >= -FM * n_lf_pre_w, name = f'fp_max_pre_caso{u}_w{w}')
            m.addConstr(fp_pre_w >= 0, name = f'fp_min_pre_caso{u}_w{w}')
            m.addConstr(-fn_pre_w >= -FM * (1 - n_lf_pre_w), name = f'fn_max_pre_caso{u}_w{w}')
            m.addConstr(fn_pre_w >= 0, name = f'fn_min_pre_caso{u}_w{w}')

        for j in range(nl):
            m.addConstr(df_pre_w[j, :].sum() == fp_pre_w[j] + fn_pre_w[j], name = f'f0_pre_{j}_caso{u}_w{w}')

        m.addConstr(f_pre_w == fp_pre_w - fn_pre_w, name = f'f1_pre_caso{u}_w{w}')
        m.addConstr(-f_pre_w - 0.5*ploss_pre_w >= -FM, name = f'fmax_loss_pre_caso{u}_w{w}')
        m.addConstr(f_pre_w - 0.5*ploss_pre_w >= -FM, name = f'fmin_loss_pre_caso{u}_w{w}')

        if ady:
            for j in range(nl):
                for l in range(L):  
                    if l == 0:
                        m.addConstr(-df_pre_w[j, l] >= -FM[j]/L, name=f'df_pre_{j}_{l}_max_caso{u}_w{w}')
                        m.addConstr(df_pre_w[j, l] >= n_df_pre_w[j, l] * FM[j]/L, name=f'df_pre_{j}_{l}_min_caso{u}_w{w}')
                    elif l == L-1:
                        m.addConstr(-df_pre_w[j, l] >= -n_df_pre_w[j, l-1] * FM[j]/L, name=f'df_pre_{j}_{l}_max_caso{u}_w{w}')
                        m.addConstr(df_pre_w[j, l] >= 0, name=f'df_pre_{j}_{l}_min_caso{u}_w{w}')
                    else:        
                        m.addConstr(-df_pre_w[j, l] >= -n_df_pre_w[j, l-1] * FM[j]/L, name=f'df_pre_{j}_{l}_max_caso{u}_w{w}')
                        m.addConstr(df_pre_w[j, l] >= n_df_pre_w[j, l] * FM[j]/L, name=f'df_pre_{j}_{l}_min_caso{u}_w{w}')

        #####################################################################################################################################
        # ==== Postcontingencia ====
        
        for k_idx,(tipo,index) in enumerate(contingencias):
            p_post_k     = p_post[:,k_idx, w]
            d_post_k     = d_post[:,k_idx, w]
            p_ens_post_k = p_ens_post[:,k_idx, w]
            f_post_k     = f_post[:,k_idx, w]
            fp_post_k    = fp_post[:,k_idx, w]
            fn_post_k    = fn_post[:,k_idx, w]
            ploss_post_k = ploss_post[:,k_idx, w]
            df_post_k    = df_post[:,:,k_idx, w]
            n_lf_post_k  = n_lf_post[:,k_idx, w]
            n_df_post_k  = n_df_post[:,:,k_idx, w]
            eta_vector_post = eta_vector.copy()

            # N-1 cargas
            if tipo == 'load':
                Load_bus_post_k = Load_bus_pre.copy()
                if index == 2:    
                    Load_bus_post_k[5] -= alm_2
                elif index == 4:    
                    Load_bus_post_k[1] -= alm_4
                elif index == 11:    
                    Load_bus_post_k[2] -= alm_11
                else:    
                    Load_bus_post_k[7] -= alm_enap

            # N-1 gen.
            elif tipo == 'gen':
                # Anular el componente estocástico para el generador fuera de servicio
                Load_bus_post_k = Load_bus_pre.copy()
                eta_vector_post[index-1] = 0
                
            else:
                Load_bus_post_k = Load_bus_pre.copy()
            
            nombre_k = f"Cont{k_idx+1}_{tipo}{index}"
            vars_case['Load_bus_post'][nombre_k] = Load_bus_post_k

            # Barra SL
            m.addConstr(d_post_k[SL] == 0, f'SL_post[{k_idx}]_caso{u}_w{w}')

            # Balance (LCK)
            m.addConstr(Cg @ p_post_k + Cg @ eta_vector_post +  p_ens_post_k - Load_bus_post_k - 0.5 * A_bar.T @ ploss_post_k == A.T @ f_post_k, name = f'LCK_post[{k_idx}]_caso{u}_w{w}')

            #####################################################################################################################################
            # Límite y pérdidas líneas post
            for j in range(nl):
                sum_kdf_post = df_post_k[j,:] @ k_coef[j,:]
                m.addConstr(ploss_post_k[j] == (g[j]/b[j]**2) * sum_kdf_post, name=f'f_lin_{j}_{k_idx}_post_caso{u}_w{w}') 

            if 1-ady:
                for l in range(0,L):
                    m.addConstr(-df_post_k[:,l] >= -FM/L, name=f'df_max_post[{k_idx}]_{l}_caso{u}_w{w}') 
                    m.addConstr(df_post_k[:,l] >= 0, name=f'df_min_post[{k_idx}]_{l}_caso{u}_w{w}')

            m.addConstr(f_post_k == -Sb * BfR @ d_post_k, name = f'LVK_post[{k_idx}]_caso{u}_w{w}')
            m.addConstr(-f_post_k >= -FM, name = f'fmax_post[{k_idx}]_caso{u}_w{w}')
            m.addConstr(f_post_k >= -FM, name = f'fmin_post[{k_idx}]_caso{u}_w{w}')

            # Sin cond. de complementariedad
            if 1-compl:
                m.addConstr(-fp_post_k >= -FM, name = f'fp_max_post[{k_idx}]_caso{u}_w{w}')
                m.addConstr(fp_post_k >= 0, name = f'fp_min_post[{k_idx}]_caso{u}_w{w}')
                m.addConstr(-fn_post_k >= -FM, name = f'fn_max_post[{k_idx}]_caso{u}_w{w}')
                m.addConstr(fn_post_k >= 0, name = f'fn_min_post[{k_idx}]_caso{u}_w{w}')
            else:
            # Con cond. de complementariedad    
                m.addConstr(-fp_post_k >= -FM * n_lf_post_k, name = f'fp_max_post[{k_idx}]_caso{u}_w{w}')
                m.addConstr(fp_post_k >= 0, name = f'fp_min_post[{k_idx}]_caso{u}_w{w}')
                m.addConstr(-fn_post_k >= -FM * (1 - n_lf_post_k), name = f'fn_max_post[{k_idx}]_caso{u}_w{w}')
                m.addConstr(fn_post_k >= 0, name = f'fn_min_post[{k_idx}]_caso{u}_w{w}')

            for j in range(nl):
                m.addConstr(df_post_k[j,:].sum() == fp_post_k[j] + fn_post_k[j], name = f'f0_post[{k_idx}]_{j}_caso{u}_w{w}')

            m.addConstr(f_post_k == fp_post_k - fn_post_k, name = f'f1_post[{k_idx}]_caso{u}_w{w}')
            m.addConstr(-f_post_k - 0.5*ploss_post_k >= -FM, name = f'fmax_loss_post[{k_idx}]_caso{u}_w{w}')
            m.addConstr(f_post_k - 0.5*ploss_post_k >= -FM, name = f'fmin_loss_post[{k_idx}]_caso{u}_w{w}')

            if ady:
                for j in range(nl):
                    for l in range(L):  
                        if l == 0:
                            m.addConstr(-df_post_k[j,l] >= -FM[j]/L, name=f'df_post[{k_idx}]_line{j}_seg{l}_max_caso{u}_w{w}')
                            m.addConstr(df_post_k[j,l] >= n_df_post_k[j,l] * FM[j]/L, name=f'df_post[{k_idx}]_line{j}_seg{l}_min_caso{u}_w{w}')
                        elif l == L-1:
                            m.addConstr(-df_post_k[j,l] >= -n_df_post_k[j,l-1] * FM[j]/L, name=f'df_post[{k_idx}]_line{j}_seg{l}_max_caso{u}_w{w}')
                            m.addConstr(df_post_k[j,l] >= 0, name=f'df_post[{k_idx}]_line{j}_seg{l}_min_caso{u}_w{w}')
                        else:        
                            m.addConstr(-df_post_k[j,l] >= -n_df_post_k[j,l-1] * FM[j]/L, name=f'df_post[{k_idx}]_line{j}_seg{l}_max_caso{u}_w{w}')
                            m.addConstr(df_post_k[j,l] >= n_df_post_k[j,l] * FM[j]/L, name=f'df_post[{k_idx}]_line{j}_seg{l}_min_caso{u}_w{w}')                          

            #####################################################################################################################################
            # Límite ángulos
            m.addConstr(-A @ d_post_k >= -pi/2, name = f'dM_post[{k_idx}]_caso{u}_w{w}')
            m.addConstr(A @ d_post_k >= -pi/2, name = f'dm_post[{k_idx}]_caso{u}_w{w}')

            # Generador fuera de servicio
            if tipo == 'gen':
                m.addConstr(p_post_k[index-1] == 0, f'Out_service[{k_idx}]_caso{u}_w{w}')
                for h in range(ng):
                    if h != index-1:   # todos excepto el fuera de servicio
                        # P_max y P_min
                        m.addConstr(p_post_k[h] + eta_vector_post[h] >= Pmin[h], name=f'Pmin_post[{k_idx},{h}]_caso{u}_w{w}')
                        m.addConstr(-p_post_k[h] - eta_vector_post[h] >= -Pmax[h], name=f'Pmax_post[{k_idx},{h}]_caso{u}_w{w}')
                                               
                        #  Gen. renovables (límite VUL)
                        if h in idx_erv:
                            m.addConstr(-p_post_k[h] >= -p_VUL, name = f'P_base_VUL[{k_idx},{h}]_caso{u}_w{w}')

                        # Reserva
                        m.addConstr(p_pre_w[h] + r_up[h] >= p_post_k[h], name=f'Up[{k_idx},{h}]_caso{u}_w{w}')
                        m.addConstr(-p_pre_w[h] + r_dn[h] >= -p_post_k[h], name=f'Dn[{k_idx},{h}]_caso{u}_w{w}')
            
            else:
                # P_max y P_min
                m.addConstr(p_post_k + eta_vector_post >= Pmin, name = f'P_min_post[{k_idx}]_caso{u}_w{w}')
                m.addConstr(-p_post_k - eta_vector_post >= -Pmax, name= f'P_max_post[{k_idx}]_caso{u}_w{w}')

                # Gen. renovables (límite VUL)
                for idx_e in idx_erv:
                    m.addConstr(-p_post_k[idx_e] >= -p_VUL, name = f'P_base_VUL[{k_idx},{idx_e}]_caso{u}_w{w}')

                # Reserva
                m.addConstr(p_pre_w + r_up >= p_post_k, name = f'Up[{k_idx}]_caso{u}_w{w}')
                m.addConstr(- p_pre_w + r_dn >= -p_post_k, name = f'Dn[{k_idx}]_caso{u}_w{w}')

            # ENS
            m.addConstr(-p_ens_post_k >= -Pmax_ens, name=f'P_max_ens_post[{k_idx}]_caso{u}_w{w}')
        
    vars_list.append(vars_case)

if not agc_u:
    C_res = r_up_g @ Cto_up_g + r_dn_g @ Cto_dn_g
else:
    C_res = u_up_g @ Cto_up_g + u_dn_g @ Cto_dn_g + (r_up_g + r_dn_g) @ (np.ones(ng_g) * 1e-6)
    #C_res = u_up_g @ Cto_up_g + u_dn_g @ Cto_dn_g + r_up_g @ Cto_up_g + r_dn_g @ Cto_dn_g

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

# Print resultados
status = m.Status
if status == GRB.Status.OPTIMAL:    
    # Obtener precios sombra
    fixed = m.fixed()
    fixed.optimize()

    print('Costo total = %.2f ($/h)' % (m.objVal))
    print('num_Vars = %d / num_Const = %d / num_NonZeros = %d' % (m.NumVars, m.NumConstrs, m.DNumNZs))
    print('Formulation time: %.4f s' % (t1-t0))
    print('Solution time: %.4f s' % (t2-t1))
    print('Solver time: %.4f s' % (m.Runtime))

    print("\n" + "=" * 5 + " Reservas " + "=" * 5)
    print('Costo de reservas: %.2f $/h' % (C_res.getValue()))
    print("-" * 25)
    
    reservas = []
    for name in gen_agc:
        matches = [key for key in dicc_gen.keys() if name in key]
        i = dicc_gen[matches[0]]
        print(f"r_up [{i+1}, {name}] = {r_up_g.X[i]:.3f} MW")    
        print(f"r_dn [{i+1}, {name}] = {r_dn_g.X[i]:.3f} MW")
        reservas.append({
            "Generador": name,
            "r_up": round(r_up_g.X[i], 3),
            "r_dn": round(r_dn_g.X[i], 3)
        })
    print("_" * 80)
    print(f" Pronóstico: {p_fore:.3f} MW  |  p_VUL: {p_VUL:.3f} MW")
    print("_" * 80)


    print("_" * 50) 

    print ('Lagrange multipliers:')
    for c in fixed.getConstrs():
        if abs(c.Pi) > 1e-2:
            print(f'{c.ConstrName} = {c.Pi:g} ($/MWh)')
elif status == GRB.Status.INF_OR_UNBD or \
    status == GRB.Status.INFEASIBLE  or \
    status == GRB.Status.UNBOUNDED:
    print('The model cannot be solved because it is infeasible or unbounded => status "%d"' % status)
    m.computeIIS()
    m.write("model_iis.ilp")
    print("IIS written to model_iis.ilp")
