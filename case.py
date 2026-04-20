from numpy import insert, int64, array, matrix, diag, zeros, ones, arange, ix_, r_, flatnonzero as find, real, imag, dot as mult
from scipy.sparse import csr_matrix as sparse, identity as sparseI
from numpy.linalg import solve

def case3b():
    ppc = {"version": '2'}

    ##-----  Power Flow Data  -----##
    ## system MVA base
    ppc["baseMVA"] = 100.0

    ## bus data
    # bus_i type  Pd  Qd  Gs  Bs  area  Vm  Va  baseKV  zone  Vmax  Vmin
    ppc["bus"] = array([
        #0    1    2   3  4   5    6     7   8    9     10     11    12
        [1,   3,   0,  0, 0,  0,   1,    1,  0,  230,    1,   1.1,   0.9],
        [2,   1,   0,  0, 0,  0,   1,    1,  0,  230,    1,   1.1,   0.9],
        [3,   1,  50,  0, 0,  0,   1,    1,  0,  230,    1,   1.1,   0.9],
    ])

    ## generator data
    #  bus, Pg, Qg, Qmax, Qmin, Vg, mBase, status, Pmax, Pmin, Pc1, Pc2,
    #  Qc1min, Qc1max, Qc2min, Qc2max, ramp_agc, ramp_10, ramp_30, ramp_q, apf
    ppc["gen"] = array([
        #0   1   2   3     4     5    6       7      8     9    10   11 12 13 14 15 16 17 18 19 20
        [1,  0,  0, 100, -100,   1,  100,     1,    50,  2.4,   0,   0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [2,  0,  0, 100, -100,   1,  100,     1,    50,  0,   0,   0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 
        [3,  0,  0, 100, -100,   1,  100,     1,    50,  2.4,   0,   0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    ])

    ## branch data
    #fbus, tbus, r, x, b, rateA, rateB, rateC, ratio, angle, status, angmin, angmax
    ppc["branch"] = array([                              #TS (0: candidate)
        [1, 2, 0.02, 0.63, 0.1025, 100, 100, 250, 0, 0, 0, -360, 360, 1], 
        [1, 3, 0.05, 0.63, 0.0775, 100, 100, 250, 0, 0, 0, -360, 360, 0],
        [2, 3, 0.09, 0.63, 0.1275, 30, 250, 250, 0, 0, 1, -360, 360, 1]
    ])

    ## generator cost data
    # 1 startup shutdown n x1 y1 ... xn yn
    # 2 startup shutdown n c(n-1) ... c0
    if 1:
        ppc["gencost"] = array([
            [2, 1500, 0, 3, 0,    50,   10],
            [2, 2000, 0, 3, 0,     0,    0], # wind
            [2, 3000, 0, 3, 0,  19.9,    5]
        ])
        # ppc["gencost"] = array([
        #     [2, 1500, 0, 3, 0,  50,   10],
        #     [2, 2000, 0, 3, 0,   3,   0.5],
        #     [2, 3000, 0, 3, 0,  19.9, 5]
        # ])        
    else:
        ppc["gencost"] = array([
            [2, 1500, 0, 2, 60,   0],
            [2, 2000, 0, 2, 100,  0],
            [2, 3000, 0, 2, 190,  0]
        ])
            
    ng = len(ppc["gen"])
    nb = len(ppc["bus"])
    nl = len(ppc["branch"])

    # Load
    if 0:
        for b in range(nb):
            if ppc['bus'][b,2] < 0:
                ppc['bus'][b,2] = 0
    
    # Transmission modeling
    # ppc['branch'][:,5] = 1000
    b = 1 / ppc['branch'][:,3]
    # b = ppc['branch'][:,3] / (ppc['branch'][:,2]**2+ppc['branch'][:,3]**2)
    f = ppc['branch'][:, 0]-1
    t = ppc['branch'][:, 1]-1
    if max(f) > nb: #sort SEPs
        aux = ppc['bus'][:,0]
        for i in range(ng):
            pos = find(aux == ppc['gen'][i,0])
            ppc['gen'][i,0] = pos + 1
        for i in range(nl): 
            pos = find(aux == ppc['branch'][i,0]) #from
            ppc['branch'][i,0] = pos + 1
            pos = find(aux == ppc['branch'][i,1]) #to
            ppc['branch'][i,1] = pos + 1
        ppc['bus'][:,0] = range(1, nb+1)
        b = 1 / ppc['branch'][:,3]
        f = ppc['branch'][:, 0]-1
        t = ppc['branch'][:, 1]-1   

    #conection gen matrix
    Cg = sparse((ones(ng), (ppc["gen"][:,0]-1, range(ng))), (nb, ng))
    ppc["Cg"] = array(Cg.todense())
    pos_g = (ppc['gen'][:,0]-1).astype(int) # gen location (astype... for integer positions in the SF matrix)
    ppc['pos_g'] = pos_g
    
    # Transmission
    # Slack bus
    slack_bus=find(ppc['bus'][:,1]==3)
    ppc['SL'] = slack_bus

    I = r_[range(nl), range(nl)]
    S = sparse((r_[ones(nl), -ones(nl)], (I, r_[f, t])), (nl, nb))
    ppc['S'] = array(S.todense())
    Sf = sparse((ones(nl), (range(nl), f)), (nl, nb))
    ppc['Sf'] = array(Sf.todense())
    St = sparse((ones(nl), (range(nl), t)), (nl, nb))
    ppc['St'] = array(St.todense())
    
    if 1: # lossless model
        Bf = sparse((r_[b, -b], (I, r_[f, t])), (nl,nb))
        Bbus = S.T * Bf    
        Bbus, Bf = Bbus.todense(), Bf.todense()
        ppc['B'] = b
        ppc['Bf'] = array(Bf)
        ppc['Bbus'] = array(Bbus)    
        buses = arange(1, nb)
        noslack = find(arange(nb) != slack_bus)
        SF = zeros((nl, nb))
        SF[:,noslack] = solve(Bbus[ix_(noslack,noslack)].T, Bf[:,noslack].T ).T
        # GGDF = zeros((nl, nb))
        # for b in range(nb):
        #     GGDF[:,b] = SF[:,b] - mult(SF, ppc['bus'][:,2]/sum(ppc['bus'][:,2]))
        PTDF = SF * S.T
        #I_PTDF = array(sparseI(nl) - PTDF)
        LODF = PTDF * sum(diag(1/(ones(nl)-diag(PTDF)))) # LODF = SF * S.T * sum(diag(1/(ones(nl)-diag(SF * S.T))))
        ppc['SF'] = SF
        # ppc['GGDF'] = GGDF
        # ppc['PTDF'] = PTDF
        # ppc['I_PTDF'] = I_PTDF        
        # ppc['LODF'] = LODF            
        
        # Transmission N-1 modeling    
        pos_lo = find(ppc['branch'][:,13]==0) 
        SF_post = []; PTDF_post = []; I_PTDF_post = [];
        for l in range(len(pos_lo)):
            SF_out = SF + array(matrix(LODF[:,pos_lo[l]]).T * matrix(SF[pos_lo[l]]))
            SF_post.insert(l, SF_out)
            PTDF_out = SF_out * S.T
            PTDF_post.insert(l, PTDF_out)
            I_PTDF_out = array(sparseI(nl) - PTDF_out)
            I_PTDF_post.insert(l, I_PTDF_out)           
        ppc['SF_post'] = SF_post
        # ppc['PTDF_post'] = PTDF_post
        # ppc['I_PTDF_post'] = I_PTDF_post
    if 1: # lossy model
        R = ppc['branch'][:,2]
        X = ppc['branch'][:,3]
        yprim = zeros(nl).astype(complex)    
        for l in range(nl):
            yprim[l] = 1/(complex(R[l],X[l]))        
        ppc['G'] = real(yprim)
        ppc['B'] = imag(yprim)
        
        # Modeling Z = R + j X
        BfR = sparse((r_[-imag(yprim), imag(yprim)], (I, r_[f, t])), (nl,nb))
        BbusR = S.T * BfR
        BbusR, BfR = BbusR.todense(), BfR.todense()
        ppc['BfR'] = array(BfR) 
        ppc['BbusR'] = array(BbusR)    
        buses = arange(1, nb)
        noslack = find(arange(nb) != slack_bus)
        SFR = zeros((nl, nb))
        SFR[:,noslack] = solve(BbusR[ix_(noslack,noslack)].T, BfR[:,noslack].T ).T
        ppc['SFR'] = SFR
    
    return ppc, tengo interés en esta parte: pos_lo = find(ppc['branch'][:,13]==0) 
        SF_post = []; PTDF_post = []; I_PTDF_post = [];
        for l in range(len(pos_lo)):
            SF_out = SF + array(matrix(LODF[:,pos_lo[l]]).T * matrix(SF[pos_lo[l]]))
            SF_post.insert(l, SF_out)
            PTDF_out = SF_out * S.T
            PTDF_post.insert(l, PTDF_out)
            I_PTDF_out = array(sparseI(nl) - PTDF_out)
            I_PTDF_post.insert(l, I_PTDF_out)           
        ppc['SF_post'] = SF_post, aquí solo calcula para la línea 1-3? cómo se puede extender para considerar las demás líneas, o se debe tener un SF_post para cada una o es mejor llevar este calculo al código principal 
