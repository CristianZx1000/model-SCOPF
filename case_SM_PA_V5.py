"""
case_SM_PA_V5.py
---------------------
Revisar diagrama sep_SM_PA_v5.pdf para ver índices y estructura del sistema.
"""

import math

# Parámetros del sistema
def get_scenarios_data(app, prj):
    scenarios_data = {}
    baseMVA=100.0

    # def. :    C.T.P. - Central Tres Puentes, C.P.A - Central Punta Arenas, P.C.N. - Planta Cabo Negro
    barras = {
            # bus, name, buses
            1:  {"name": "Celdas 11.5kV",               "buses": ["Terminal(5).ElmTerm", "Celdas 11.5 kV BBC.ElmTerm", "Celdas 11.5 RHONA.ElmTerm", "Extensión Celdas CTP.ElmTerm"]},
            2:  {"name": "Barra principal de 13.2kV_a", "buses": ["Barra Principal de 13.2 kV.ElmTerm", "Nuevas Diesel MT.ElmTerm"]},
            3:  {"name": "Barra principal de 13.2kV_b", "buses": ["Secc.ElmTerm"]},
            4:  {"name": "C.T.P. 66kV",                 "buses": ["C.T.P. - 66 kV.ElmTerm"]},
            5:  {"name": "C.P.A. 66kV",                 "buses": ["C.P.A. - 66 kV.ElmTerm"]},
            6:  {"name": "Celdas G.E. 13.2kV",          "buses": ["Celdas G.E. 13.2 kV.ElmTerm"]},
            7:  {"name": "C.T.P. - 23 kV",              "buses": ["C.T.P. - 23 kV.ElmTerm"]},
            8:  {"name": "P.C.N. ENAP",                 "buses": ["Punto Conexión PE VPatagónicos 23.ElmTerm", "Poste vértice 183.ElmTerm"]},
            9:  {"name": "PE VPatagónicos 23/CC",       "buses": ["CC", "PE VPatagónicos SSAA 0.38.ElmTerm"]},
            10: {"name": "WTG1",                        "buses": ["WTG1.ElmTerm"]},
            11: {"name": "WTG1 0.65",                   "buses": ["WTG1 0.65.ElmTerm"]},
            12: {"name": "WTG2",                        "buses": ["WTG2.ElmTerm"]},
            13: {"name": "WTG3 0.65",                   "buses": ["WTG3 0.65.ElmTerm"]},
            14: {"name": "WTG3",                        "buses": ["WTG3.ElmTerm"]},
            15: {"name": "WTG3 0.65",                   "buses": ["WTG3 0.65.ElmTerm"]},
            16: {"name": "Barra BT 400V UG N°10",       "buses": ["Barra BT 400V UG N°10.ElmTerm"]},
            17: {"name": "Barra BT 400V UG N°11",       "buses": ["Barra BT 400V UG N°11.ElmTerm"]},
            18: {"name": "Barra BT 400V UG N°12",       "buses": ["Barra BT 400V UG N°12.ElmTerm"]},
            19: {"name": "Barra BT 400V UG N°13",       "buses": ["Barra BT 400V UG N°13.ElmTerm"]},
            20: {"name": "Barra BT 400V UG N°14",       "buses": ["Barra BT 400V UG N°14.ElmTerm"]}
        }

    gen_bus_AGC = {
        # name, bus, vf_AGC
        "Unidad Nº 4 Solar Mars.ElmSym":  {"bus": 1,  "vf": 1},
        "Unidad Nº 5 Caterpillar.ElmSym": {"bus": 2,  "vf": 0},
        "Unidad Nº 7 Solar Titan.ElmSym": {"bus": 1,  "vf": 1},
        "Unidad Nº 8 GE10.ElmSym":        {"bus": 1,  "vf": 0},
        "Unidad Nº 9 Solar Titan.ElmSym": {"bus": 1,  "vf": 1},
        "UG N°10.ElmSym":                 {"bus": 16, "vf": 0},
        "UG N°11.ElmSym":                 {"bus": 17, "vf": 0},
        "UG N°12.ElmSym":                 {"bus": 18, "vf": 0},
        "UG N°13.ElmSym":                 {"bus": 19, "vf": 0},
        "UG N°14.ElmSym":                 {"bus": 20, "vf": 0},
        "WTG1.ElmGenstat":                {"bus": 11, "vf": 1},
        "WTG2.ElmGenstat":                {"bus": 13, "vf": 1},
        "WTG3.ElmGenstat":                {"bus": 15, "vf": 1}
    }

    gen_agc_info = [
        name.replace(".ElmSym", "").replace(".ElmGenstat", "")
        for name, info in gen_bus_AGC.items()
        if info["vf"] == 1
    ]

    scenarios_data["sistema"] = {
        "baseMVA": baseMVA,
        "buses": barras,
        "dicc_gen_agc": gen_bus_AGC,
        "gen_agc_info": gen_agc_info,
        "lines": [],
        "trafos": [],
    }
    
    scenarios_data["casos"] = {}

    orden_gen = list(gen_bus_AGC.keys())
    nb = len(barras.keys())

    # Diccionario para almacenar objetos de generadores (se llena en u==1)
    generators_objects = {}

    for u in range(1, 7):
        if u == 3:
            continue

        # Seleccionar escenario
        nombre_escenario = f"CASO {u}"
        escenario = prj.GetContents(nombre_escenario, 1)[0]
        escenario.Activate()

        scenarios_data["casos"][nombre_escenario] = {
            "gen_list": []
        }

        if u == 1:
            # Generadores activos
            gen_list = [g.loc_name + ".ElmSym" for g in app.GetCalcRelevantObjects('*.ElmSym') 
                        if g.GetAttribute('outserv') == 0] + \
                        [g.loc_name + ".ElmGenstat" for g in app.GetCalcRelevantObjects('*.ElmGenstat') 
                        if g.GetAttribute('outserv') == 0]
            
            scenarios_data["casos"][nombre_escenario]["gen_list"] = gen_list

            # === Generadores ElmSym ===
            gens = app.GetCalcRelevantObjects('*.ElmSym')
            gens_sorted_sym = sorted(
                [g for g in gens if g.loc_name + ".ElmSym" in orden_gen],
                key=lambda g: orden_gen.index(g.loc_name + ".ElmSym")
            )
            for g in gens_sorted_sym:
                name = g.loc_name + ".ElmSym"
                Pmax = g.GetAttribute('Pmax_uc')
                Pmin = g.GetAttribute('Pmin_uc')

                # Buscar en el diccionario de asignaciones
                gen_info = gen_bus_AGC.get(name)
                # Bus numérico desde 'gen_bus_AGC'
                bus_num = gen_info["bus"]

                # Obtener costo variable y costo fijo
                cost_pf  = g.GetAttribute('penaltyCosts')
                fixed_pf = g.GetAttribute('fixedCosts')

                # Guardar objeto para verificar estado en otros casos
                generators_objects[name] = g

                if "generators_data" not in scenarios_data["sistema"]:
                    scenarios_data["sistema"]["generators_data"] = {}

                scenarios_data["sistema"]["generators_data"][name] = {
                    "name": name,
                    "bus": bus_num,
                    "Pmax": round(Pmax, 3),
                    "Pmin": round(Pmin, 3),
                    "vf": gen_info["vf"],
                    "cost_pf":    round(cost_pf, 5),
                    "cost_fixed": round(fixed_pf, 5)
                }

            # === Generadores ElmGenstat ===
            gens = app.GetCalcRelevantObjects('*.ElmGenstat')
            gens_sorted_genstat = sorted(
                [g for g in gens if g.loc_name + ".ElmGenstat" in orden_gen],
                key=lambda g: orden_gen.index(g.loc_name + ".ElmGenstat")
            )
            for g in gens_sorted_genstat:
                name = g.loc_name + ".ElmGenstat"
                Pmax = g.GetAttribute('Pmax_uc')
                Pmin = g.GetAttribute('Pmin_uc')

                # Buscar en el diccionario de asignaciones
                gen_info = gen_bus_AGC.get(name)
                # Bus numérico desde 'sistema["buses"]'
                bus_num = gen_info["bus"]

                # Obtener costo variable y costo fijo
                cost_pf  = g.GetAttribute('penaltyCosts')
                fixed_pf = g.GetAttribute('fixedCosts')

                # Guardar objeto para verificar estado en otros casos
                generators_objects[name] = g

                scenarios_data["sistema"]["generators_data"][name] = {
                    "name": name,
                    "bus": bus_num,
                    "Pmax": round(Pmax, 3),
                    "Pmin": round(Pmin, 3),
                    "vf": gen_info["vf"],
                    "cost_pf":    round(cost_pf, 5),
                    "cost_fixed": round(fixed_pf, 5)
                }
        
        # Generadores activos
        # usar objetos guardados previamente
        gen_list = [gen_name for gen_name, gen_obj in generators_objects.items() 
                    if gen_obj.GetAttribute('outserv') == 0]

        scenarios_data["casos"][nombre_escenario]["gen_list"] = gen_list
    
        # Lista de líneas
        if u == 1:

            lineas_interes = [
                # name, from, to
                ("Línea de unión en 66 kV.ElmLne", 4, 5),
                ("Estructura 187-Central Tres Puentes.ElmLne", 7, 8),
                ("PE VPatagónicos-Estructura 187_a.ElmLne", 7, 8),
                ("Línea Subterránea.ElmLne", 8, 9),
                ("PE VPatagónicos WTG1-PE VPatagónicos CC.ElmLne", 9, 10),
                ("WTG1-WTG2.ElmLne", 10, 12),
                ("WTG2-WTG3.ElmLne", 12, 14)
            ]

            #for nombre, fbus, tbus, Vbase in lineas_interes:
            for nombre, fbus, tbus in lineas_interes:
                line = app.GetCalcRelevantObjects(nombre)[0]

                tipo = line.typ_id
                clase_tipo = tipo.GetClassName()
                
                if clase_tipo == 'TypLne':
                    Vbase = tipo.uline
                elif clase_tipo == 'TypTow':
                    # Obtener los circuitos y tipos de conductores
                    conductores = tipo.pcond_c
                    # Acceder al circuito 1 y su tipo de conductor (TypCon)
                    tipo_conductor = conductores[0]
                    Vbase = tipo_conductor.uline

                Inom = line.GetAttribute("Inom_a")
                R = line.GetAttribute("R1") * baseMVA / Vbase**2
                X = line.GetAttribute("X1") * baseMVA / Vbase**2
                
                # Cálculo de Smax (en MVA)
                Smax = math.sqrt(3) * Vbase * Inom
                
                scenarios_data["sistema"]["lines"].append({
                    "name": line.loc_name,
                    "fbus": fbus,
                    "tbus": tbus,
                    "R": round(R, 5),
                    "X": round(X, 5),
                    "Smax": round(Smax, 2),
                })

            # Lista de trafos 
            trafos_interes = [
                # name, from, to
                ("Tres Puentes Tusan 20 MVA.ElmTr3", 1, 2),     # 20 MVA
                ("Tres Puentes Sindelen 14 MVA.ElmTr2", 1, 3),  # 14 MVA
                ("Trafo Nº 5 C.T.P..ElmTr2", 1, 4),             # 33 MVA hacia barra 66 kV
                ("Trafo 69/12 kV Rhona 1996 CTP.ElmTr2", 1, 4), # 33 MVA hacia barra 66 kV
                ("Trafo Nº 7 C.P.A..ElmTr2", 5, 6),  # 33 MVA hacia barra 66 kV
                ("Trafo Nº 1 C.T.P..ElmTr2", 1, 7),  # 12 MVA 23kV
                ("WTG1 23/0.66.ElmTr2", 10, 11),   # 4 MVA 23kV
                ("WTG2 23/0.66.ElmTr2", 12, 13),   # 4 MVA 23kV
                ("WTG3 23/0.66.ElmTr2", 14, 15),   # 4 MVA 23kV
                ("Trafo UG N°10.ElmTr2", 2, 16),   # 2.5 MVA 13.2kV
                ("Trafo UG N°11.ElmTr2", 2, 17),   # 2.5 MVA 13.2kV
                ("Trafo UG N°12.ElmTr2", 2, 18),   # 2.5 MVA 13.2kV
                ("Trafo UG N°13.ElmTr2", 2, 19),   # 2.5 MVA 13.2kV
                ("Trafo UG N°14.ElmTr2", 2, 20)    # 2.5 MVA 13.2kV
            ]

            for nombre, fbus, tbus in trafos_interes:
                TR = app.GetCalcRelevantObjects(nombre)[0]
                tipo = TR.typ_id
                
                # Diferenciar si es trafo de 3 devanados (Tr3) o 2 (Tr2)
                if TR.GetClassName() == "ElmTr3":
                    Snom = TR.GetAttribute("Snom_h_a")  # potencia nominal lado de alta
                    Xr = (tipo.uktr3_h / 100) * baseMVA / Snom
                    Rr = 0
                else:  # ElmTr2
                    Snom = TR.GetAttribute("Snom_a")
                    tap_porc = TR.GetAttribute('t:dutap') / 100
                    tap_pos = TR.GetAttribute('nntap')
                    Zr = (tipo.uktr / 100) * (1 + tap_porc * tap_pos) * baseMVA / Snom      # % --> p.u.(+ cambio de base)
                    Rr = (tipo.pcutr / 1000) * (1 + tap_porc * tap_pos) * baseMVA / Snom**2  # kW --> MW --> p.u.
                    Xr = np.sqrt(Zr**2 - Rr**2) 

                scenarios_data["sistema"]["trafos"].append({
                    "name": TR.loc_name,
                    "fbus": fbus,
                    "tbus": tbus,
                    "Snom": round(Snom, 2),
                    "R": round(Rr, 5),
                    "X": round(Xr, 5)
                })
        
        """
        Tap Trafo Nº7 C.P.A.
        Modificar recalculando la impedancia
        Almacenar la impedancia de todos los casos
        """
    
        TR = app.GetCalcRelevantObjects("Trafo Nº 7 C.P.A..ElmTr2")[0]
        tipo = TR.typ_id
        Snom = TR.GetAttribute("Snom_a")
        tap_porc = TR.GetAttribute('t:dutap') / 100
        tap_pos = TR.GetAttribute('nntap')
        Xr = (tipo.uktr / 100) * (1 + tap_porc * tap_pos) * baseMVA / Snom
        
        scenarios_data["casos"][nombre_escenario]["X_trafo_7"] = round(Xr, 6)
      
        # Cargas
        Pd_bus = [0.0 for _ in range(nb)]
        A2, A4, A11 = None, None, None

        # 1) Alimentadores ElmLod
        for l in app.GetCalcRelevantObjects('*.ElmLod'):
            if l.loc_name.startswith("Alimentador"):
                # Extraer número del alimentador
                num = int(l.loc_name.split()[1])
                pl = round(l.GetAttribute('plini'), 3)
                if num == 2:
                    A2 = pl
                if num == 4:
                    A4 = pl
                if num == 11:
                    A11 = pl
                bus = 2 if num in [4, 5, 7, 13] else (3 if num in [6, 11] else 6) # alm 6 no necesario [6, 11] -->[11], alm se calcula más abajo
                Pd_bus[bus-1] += pl

        # 2) Alimentador 6 (LdFP)
        lf = app.GetFromStudyCase('ComLdf')
        lf.Execute()
        interruptor = app.GetCalcRelevantObjects('Breaker/Switch(12).ElmCoup')[0]
        A6 = interruptor.GetAttribute('m:P:bus1')
        Pd_bus[3-1] += round(A6, 3)

        # 3) Planta Cabo Negro ENAP
        enap = app.GetCalcRelevantObjects('Planta Cabo Negro ENAP.ElmLod')[0]
        enap_load = round(enap.GetAttribute('plini'), 3)
        Pd_bus[8-1] += enap_load

        # 4) Servicios auxiliares Vientos Patagónicos
        ssaa_VP = app.GetCalcRelevantObjects('PE VPatagónicos SSAA.ElmLod')[0]
        Pd_bus[9-1] += round(ssaa_VP.GetAttribute('plini'), 3)

        scenarios_data["casos"][nombre_escenario]["A_max"] = {"A2": A2, "A4": A4, "A11": A11, "enap": enap_load}
        Pd_bus = [round(val, 3) for val in Pd_bus]
        scenarios_data["casos"][nombre_escenario]["Pd_bus"] = Pd_bus
        
    return scenarios_data

def compute_costs(scenarios_data, cdn=1.0, u_term=0.7, u_wtg=0.1, u_su=0.2):
    gen_data = scenarios_data["sistema"]["generators_data"]
    dicc_gen = scenarios_data["sistema"]["dicc_gen_agc"]

    costo_max_termica_agc = max(
        gen_data[name]["cost_pf"]
        for name, info in dicc_gen.items()
        if info["vf"] == 1 and "WTG" not in name
    )

    for name, info in dicc_gen.items():
        cost_pf  = gen_data[name]["cost_pf"]
        fixed_pf = gen_data[name]["cost_fixed"]
        vf       = info["vf"]
        es_wtg   = "WTG" in name

        if es_wtg:
            cost   = [0, fixed_pf]
            Cto_up = u_wtg * costo_max_termica_agc if vf == 1 else 0
            Cto_dn = u_wtg * costo_max_termica_agc if vf == 1 else 0
            c_su = 0
        else:
            cost   = [cdn * cost_pf, fixed_pf]
            Cto_up = u_term * cost_pf if vf == 1 else 0
            Cto_dn = u_term * cost_pf if vf == 1 else 0
            c_su   = u_su * cost_pf

        # Actualizar ambos diccionarios
        info["cost"]   = cost
        info["Cto_up"] = Cto_up
        info["Cto_dn"] = Cto_dn
        info["c_su"]   = c_su

        gen_data[name]["cost"]   = cost
        gen_data[name]["Cto_up"] = Cto_up
        gen_data[name]["Cto_dn"] = Cto_dn
        gen_data[name]["c_su"]   = c_su

    return scenarios_data

import numpy as np
from numpy import ones, arange, r_, imag
from scipy.sparse import csr_matrix as sparse
from scipy.linalg import solve

def reduce_branches(lines, trafos):    
    # Combinar líneas y trafos
    branch_total = []
    
    for l in lines:
        branch_total.append({
            "name": l["name"],
            "fbus": l["fbus"],
            "tbus": l["tbus"],
            "R": l["R"],
            "X": l["X"],
            "Smax": l["Smax"],
            "is_trafo": False
        })
    
    for t in trafos:
        branch_total.append({
            "name": t["name"],
            "fbus": t["fbus"],
            "tbus": t["tbus"],
            "R": t["R"],
            "X": t["X"],
            "Smax": t["Snom"],
            "is_trafo": True
        })
    
    # ===== Reducción 1: Bus 1-4 =====
    # 2 trafos en paralelo
    branches_14 = [b for b in branch_total if {b["fbus"], b["tbus"]} == {1, 4}]
    
    if branches_14:
        trafos_14 = [b for b in branches_14 if b["is_trafo"]]
        
        if len(trafos_14) == 2:
            tr1, tr2 = trafos_14
            
            # Paralelo de tr1 y tr2
            Z_tr1 = complex(0, tr1["X"])
            Z_tr2 = complex(0, tr2["X"])
            Z_eq = (Z_tr1 * Z_tr2) / (Z_tr1 + Z_tr2)
            
            R_eq = Z_eq.real
            X_eq = Z_eq.imag
            
            razon1 = tr2["X"] / (tr1["X"] + tr2["X"])
            razon2 = tr1["X"] / (tr1["X"] + tr2["X"]) 

            Smax1 = tr1["Smax"] / razon1
            Smax2 = tr2["Smax"] / razon2

            Smax_eq = min(Smax1, Smax2)
            
            # Eliminar originales y agregar equivalente
            branch_total = [b for b in branch_total if {b["fbus"], b["tbus"]} != {1, 4}]
            branch_total.append({
                "name": "Equivalente 1-4 (reducido)",
                "fbus": 1, "tbus": 4,
                "R": R_eq, "X": X_eq,
                "Smax": Smax_eq,
                "is_trafo": False
            })
    
    # ===== Reducción 2: Bus 7-8 =====
    # 2 líneas en serie
    branches_78 = [b for b in branch_total if {b["fbus"], b["tbus"]} == {7, 8}]
    
    if branches_78:
        lineas_78 = [b for b in branches_78 if not b["is_trafo"]]
        
        if len(lineas_78) == 2:
            linea1, linea2 = lineas_78
            
            # Serie
            Z_line1 = complex(linea1["R"], linea1["X"])
            Z_line2 = complex(linea2["R"], linea2["X"])
            Z_eq = Z_line1 + Z_line2
            
            R_eq = Z_eq.real
            X_eq = Z_eq.imag
            Smax_eq = linea1["Smax"]
            
            # Eliminar originales y agregar equivalente
            branch_total = [b for b in branch_total if {b["fbus"], b["tbus"]} != {7, 8}]
            branch_total.append({
                "name": "Equivalente 7-8 (reducido)",
                "fbus": 7, "tbus": 8,
                "R": R_eq, "X": X_eq,
                "Smax": Smax_eq,
                "is_trafo": False
            })
    
    # Ordenar por fbus, tbus
    branch_total.sort(key=lambda b: (b["fbus"], b["tbus"]))
    
    return branch_total

def calculate_reduced_X_trafo_7(scenarios_data, caso_name):
    sistema = scenarios_data["sistema"]
    caso = scenarios_data["casos"][caso_name]
    
    # Obtener trafo 7
    trafo_7 = [t for t in sistema["trafos"] 
                 if {t["fbus"], t["tbus"]} == {5, 6}]
    
    if not trafo_7:
        return None
    
    # Identificar trafos por nombre
    # 2 trafos en paralelo en bus 1, 1 trafo en bus 4
    trafo_tap = None # El trafo que cambia su tap es el "Trafo Nº 7 C.P.A."

    for tr in trafo_7:
        if "Trafo Nº 7 C.P.A." in tr["name"]:
            trafo_tap = tr
            
    if not trafo_tap:
        print(f"Error: No se encontró correctamente el 'Trafo Nº 7 C.P.A.'")
        return None
    
    # Usar X actualizado con tap del caso
    X_trafo_tap = caso["X_trafo_7"]
    
    return X_trafo_tap  # Retornar solo la parte imaginaria (X)

def build_network_matrices(scenarios_data, baseMVA=100.0, eps_x=1e-9):
    sistema = scenarios_data["sistema"]
    nb = len(sistema["buses"])
    
    # ===== Aplicar reducciones =====
    branch_reduced = reduce_branches(sistema["lines"], sistema["trafos"])
    
    nl = len(branch_reduced)
    
    # ===== Extraer vectores =====
    fbus = []
    tbus = []
    R = []
    X = []
    Smax = []
    
    for b in branch_reduced:
        fbus.append(b["fbus"])
        tbus.append(b["tbus"])
        R.append(round(b["R"], 6))
        X.append(round(b["X"], 6))
        Smax.append(round(b["Smax"], 3))
    
    # Convertir a arrays (0-indexed)
    f = np.array(fbus, dtype=int) - 1
    t = np.array(tbus, dtype=int) - 1
    R = np.array(R)
    X_base = np.array(X)
    Smax = np.array(Smax)
    
    # ===== Matrices de incidencia (NO cambian) =====
    I = r_[arange(nl), arange(nl)]
    
    S = sparse((r_[ones(nl), -ones(nl)], (I, r_[f, t])), 
               shape=(nl, nb)).toarray()
    
    Sf = sparse((ones(nl), (arange(nl), f)), 
                shape=(nl, nb)).toarray()
    
    St = sparse((ones(nl), (arange(nl), t)), 
                shape=(nl, nb)).toarray()
    
    A_bar = Sf + St
    
    # ===== Identificar índice del trafo 5-6 =====
    # trafo con tap variable (Trafo Nº 7 C.P.A.)
    idx_trafo_7 = None
    for i, b in enumerate(branch_reduced):
        # Buscar el trafo entre buses 5-6
        if b["fbus"] == 5 and b["tbus"] == 6 and "Trafo Nº 7 C.P.A." in b["name"]:
            idx_trafo_7 = i
            break

    network = {
        "nb": nb,
        "nl": nl,
        "f": f,
        "t": t,
        "R": R,
        "X_base": X_base,
        "Smax": Smax,
        "S": S,
        "Sf": Sf,
        "St": St,
        "A_bar": A_bar,
        "baseMVA": baseMVA,
        "eps_x": eps_x,
        "idx_trafo_7": idx_trafo_7,  # Para actualizar trafo con tap
        "branch_info": branch_reduced   # Info completa de branches
    }
    
    return network

def compute_sensitivity_matrices(network, X_trafo_7_new, slack_bus=0):
    nb = network["nb"]
    nl = network["nl"]
    f = network["f"]
    t = network["t"]
    S = network["S"]
    eps_x = network["eps_x"]
    
    # ===== Actualizar X del trafo 5-6 =====
    X = network["X_base"].copy()
    
    if network["idx_trafo_7"] is not None:
        # X_trafo_7_new es simplemente la X del trafo con el tap actualizado
        X[network["idx_trafo_7"]] = X_trafo_7_new
    
    R = network["R"]
    
    # ===== Modelo SIN pérdidas =====
    X_safe = np.where(np.abs(X) < eps_x, eps_x, X)
    b = 1.0 / X_safe
    
    I = r_[arange(nl), arange(nl)]
    Bf = sparse((r_[b, -b], (I, r_[f, t])), shape=(nl, nb)).toarray()
    Bbus = S.T.dot(Bf)
    
    # Flow Sensitivity Factor (SF)
    noslack = np.where(np.arange(nb) != slack_bus)[0]
    SF = np.zeros((nl, nb))
    
    try:
        SF[:, noslack] = solve(Bbus[np.ix_(noslack, noslack)].T, 
                               Bf[:, noslack].T).T
    except:
        print("Warning: No se pudo calcular SF")
    
    # ===== Modelo CON pérdidas =====
    yprim = np.zeros(nl, dtype=complex)
    for l in range(nl):
        z = complex(R[l], X[l])
        if abs(z) < 1e-12:
            yprim[l] = 0 + 0j
        else:
            yprim[l] = 1.0 / z
    
    g = np.real(yprim)
    b_lossy = np.imag(yprim)
    
    BfR = np.zeros((nl, nb))
    for i in range(nl):
        bval = imag(yprim[i])
        BfR[i, f[i]] = -bval
        BfR[i, t[i]] = bval
    
    BbusR = S.T.dot(BfR)
    
    # Flow Sensitivity con pérdidas (SFR)
    SFR = np.zeros((nl, nb))
    try:
        SFR[:, noslack] = solve(BbusR[np.ix_(noslack, noslack)].T, 
                                BfR[:, noslack].T).T
    except:
        print("Warning: No se pudo calcular SFR")
    
    matrices = {
        "Bf": Bf,
        "Bbus": Bbus,
        "SF": SF,
        "BfR": BfR,
        "BbusR": BbusR,
        "SFR": SFR,
        "g": g,
        "b": b_lossy,
        "X": X,
        "R": R
    }
    
    return matrices

def prepare_case_data(scenarios_data, network, caso_name, matrices):
    sistema = scenarios_data["sistema"]
    caso = scenarios_data["casos"][caso_name]
    
    # ===== Generadores activos =====
    gen_list = caso["gen_list"]
    ng = len(gen_list)
    
    Pmax = []
    Pmin = []
    gen_bus = []
    a_g = []
    b_g = []
    c_su = []
    Cto_up = []
    Cto_dn = []
    vf = []
    g_names = []
    
    for gen_name in gen_list:
        gen_data = sistema["generators_data"][gen_name]
        
        Pmax.append(gen_data["Pmax"])
        Pmin.append(gen_data["Pmin"])
        gen_bus.append(gen_data["bus"] - 1)  # 0-indexed
        a_g.append(gen_data["cost"][0])
        b_g.append(gen_data["cost"][1])
        c_su.append(gen_data["c_su"])
        Cto_up.append(gen_data["Cto_up"])
        Cto_dn.append(gen_data["Cto_dn"])
        vf.append(gen_data["vf"])
        g_names.append(gen_name)
    
    Pmax = np.array(Pmax)
    Pmin = np.array(Pmin)
    gen_bus = np.array(gen_bus, dtype=int)
    a_g = np.array(a_g)
    b_g = np.array(b_g)
    c_su = np.array(c_su)
    Cto_up_g = np.array(Cto_up)
    Cto_dn_g = np.array(Cto_dn)
    vf = np.array(vf)
    
    # ===== Matriz Cg =====
    nb = network["nb"]
    Cg = sparse((ones(ng), (gen_bus, np.arange(ng))), 
                shape=(nb, ng)).toarray()
    
    # ===== Datos del caso =====
    data = {
        # Sistema
        "Sb": network["baseMVA"],
        "SL": 0,
        "ng": ng,
        "nb": nb,
        "nl": network["nl"],
        
        # Generadores
        "Pmax": Pmax,
        "Pmin": Pmin,
        "a_g": a_g,
        "b_g": b_g,
        "c_su": c_su,
        "Cto_up_g": Cto_up_g,
        "Cto_dn_g": Cto_dn_g,
        "g_names": g_names,
        "vf": vf,
        
        # Topología
        "branch_f": network["f"] + 1,  # 1-indexed
        "branch_t": network["t"] + 1,
        "FM": network["Smax"],
        "Cg": Cg,
        
        # Matrices de red
        "A": network["S"],
        "A_bar": network["A_bar"],
        "Sf": network["Sf"],
        "St": network["St"],
        
        # Sensibilidad
        "Bf": matrices["Bf"],
        "Bbus": matrices["Bbus"],
        "SF": matrices["SF"],
        "BfR": matrices["BfR"],
        "BbusR": matrices["BbusR"],
        "SFR": matrices["SFR"],
        "g": matrices["g"],
        "b": matrices["b"],
        
        # Cargas
        "Load_bus_pre": np.array(caso["Pd_bus"]),
        "alm_2": caso["A_max"]["A2"],
        "alm_4": caso["A_max"]["A4"],
        "alm_11": caso["A_max"]["A11"],
        "alm_enap": caso["A_max"]["enap"]
    }
    
    return data
