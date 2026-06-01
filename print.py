# Print resultados    
status = m.Status
if status == GRB.Status.OPTIMAL:    
    # Obtener precios sombra
    fixed = m.fixed()
    # for v in fixed.getVars():
    #     if v.LB > v.UB - 1e-10:  # límites casi iguales (var fijada)
    #         v.LB -= 1e-6
    #         v.UB += 1e-6
    # fixed.Params.FeasibilityTol = 1e-4
    fixed.optimize()

    # if fixed.Status != GRB.Status.OPTIMAL:
    #     print(f"! fixed.optimize() no es óptimo (status={fixed.Status}). No se pueden obtener LMPs.")

    # n_fractional = sum(1 for v in m.getVars() 
    #                if v.Vtype in (GRB.BINARY, GRB.INTEGER) 
    #                and abs(v.X - round(v.X)) > 1e-6)
    # print(f"Variables binarias con valor no exactamente entero: {n_fractional}")

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

    ##############################################################
    if False:
        import re
        print ('Lagrange multipliers:','\n Precios nodales (LMP) pre')
        imprimir_all = False
        imprimir_scenarios_w = [1]

        factor_pre = 5 * n_w
        for c in fixed.getConstrs():
            if "LCK_pre" in c.ConstrName:
                # Busca: LCK_pre_caso{u}_w{w}[{b}]
                match = re.search(r'_caso(\d+)_w(\d+)\[(\d+)\]', c.ConstrName)
                if match:
                    u_str = int(match.group(1))
                    w_str = int(match.group(2))
                    bus_idx = int(match.group(3))
                    if imprimir_all or (w_str in imprimir_scenarios_w):
                        lmp_real = c.Pi * factor_pre
                        if abs(lmp_real) > 1e-2:
                            print(f'Caso {u_str} | Esc {w_str} | Barra {bus_idx+1}:\t LMP = {lmp_real:.2f} ($/MWh)')
        
        #-----------------------------------

        print('\n--- Post-contingencia ---')
        # Recuperar el 'K' real de cada caso
        K_por_caso = {}
        for i, u_val in enumerate(casos_ejecutar):
            K_por_caso[u_val] = len(vars_list[i]['contingencias'])
        
        for c in fixed.getConstrs():
            if "LCK_post" in c.ConstrName:
                # Busca: LCK_post[{k}]_caso{u}_w{w}[{b}]
                match = re.search(r'\[(\d+)\]_caso(\d+)_w(\d+)\[(\d+)\]', c.ConstrName)
                if match:
                    k_idx = int(match.group(1))
                    u_str = int(match.group(2))
                    w_str = int(match.group(3))
                    bus_idx = int(match.group(4))
                    
                    if imprimir_all or (w_str in imprimir_scenarios_w):
                        K_u = K_por_caso[u_str]
                        factor_post = 5 * n_w * K_u
                        
                        lmp_real = c.Pi * factor_post
                        if abs(lmp_real) > 1e-2:
                            print(f'Caso {u_str} | Esc {w_str} | Cont {k_idx+1} | Barra {bus_idx+1}:\t LMP = {lmp_real:.2f} ($/MWh)')

    ##############################################################

    if False:
        casos_elegidos = [1]          # lista de casos a mostrar (1 a 6)
        escenarios_w_elegidos = [0]   # lista de escenarios de incertidumbre a mostrar (1 a n_w)
        contingencias_elegidas = [1]  # lista de contingencias a mostrar
        
        for w_idx, w in enumerate(escenarios_w_elegidos):
            w_real = w - 1  # convertir a índice 0-based
            eta_w = eta_list[w_real]
            
            print("\n" + "=" * 70)
            print(f" Escenario de incertidumbre {w}")
            print(f" Incertidumbre: {epsilon_list[w]:.3f} MW  |  eta: {eta_list[w]:.3f} MW")
            print("=" * 70)
            
            for u_idx, u in enumerate(casos_elegidos):
                u_real = u - 1  # convertir a índice 0-based
                
                if u_real >= len(vars_list):
                    print(f"\nCaso {u} no existe (solo hay {len(vars_list)} casos)")
                    continue
                
                vars_case = vars_list[u_real]
                nombre_caso = f"CASO {u}"
                
                p_pre = vars_case['p_pre']
                f_pre = vars_case['f_pre']
                ploss_pre = vars_case['ploss_pre']
                p_post = vars_case['p_post']
                f_post = vars_case['f_post']
                p_ens_post = vars_case['p_ens_post']
                ploss_post = vars_case['ploss_post']
                Cop_pre = vars_case['Cop_pre']
                Cop_post = vars_case['Cop_post']
                
                gen_names = vars_case['gen_names']
                branch_from = vars_case['branch_from']
                branch_to = vars_case['branch_to']
                contingencias = vars_case['contingencias']
                
                nb = p_ens_post.shape[0]
                ng = p_pre.shape[0]
                nl = f_pre.shape[0]
                K = p_post.shape[1]
                n_w_caso = p_pre.shape[1]
                
                if w_real >= n_w_caso:
                    print(f"\nEscenario de incertidumbre {w} no existe para el caso {u}")
                    continue
                
                print("\n" + "-" * 70)
                print(f"  {nombre_caso}")
                print("-" * 70)
                
                print(f"\nCosto precontingencia: {Cop_pre.getValue():.2f} $/h")
                print(f"Costo postcontingencia: {Cop_post.getValue():.2f} $/h")
                
                print("\n" + "-" * 50)
                print("Índice de generadores:")
                print("-" * 50)
                for h, g_name in enumerate(gen_names):
                    clean_name = g_name.replace('.ElmSym', '').replace('.ElmGenstat', '')
                    print(f"  [{h+1}] {clean_name}")
                
                # Precontingencia
                print("\n" + "-" * 50)
                print(f"Precontingencia (incertidumbre w={w})")
                print("-" * 50)
                
                print('\nPotencias generadores:')
                for h in range(ng):
                    clean_name = gen_names[h].replace('.ElmSym', '').replace('.ElmGenstat', '')
                    print(f"  p_pre[{h+1:2d}, {clean_name:30s}] = {p_pre.X[h, w_real]:7.3f} MW")
                
                print('\nFlujos líneas:')
                for l in range(nl):
                    print(f"  f_pre[{branch_from[l]:2.0f} -> {branch_to[l]:2.0f}] = {f_pre.X[l, w_real]:7.3f} MW")
                
                print(f'\nPérdidas totales: {ploss_pre.X[:, w_real].sum():.3f} MW')
                
                # Postcontingencia
                print("\n" + "-" * 50)
                print(f"Postcontingencia (incertidumbre w={w})")
                print("-" * 50)
                
                for c_idx, c in enumerate(contingencias_elegidas):
                    c_real = c - 1  # convertir a índice 0-based
                    
                    if c_real >= K:
                        print(f"\nContingencia {c} no existe (solo hay {K} contingencias)")
                        continue
                    
                    tipo, idx = contingencias[c_real]
                    
                    print(f"\n{'>' * 35}")
                    if tipo == "load":
                        if idx == 2:
                            print(f"Contingencia {c}: Alimentador 2 desconectado")
                        elif idx == 4:
                            print(f"Contingencia {c}: Alimentador 4 desconectado")
                        else:
                            print(f"Contingencia {c}: Alimentador ENAP desconectado")
                    else:
                        gen_name_out = gen_names[idx-1].replace('.ElmSym', '').replace('.ElmGenstat', '')
                        print(f"Contingencia {c}: Generador {idx} ({gen_name_out}) fuera")
                    print('>' * 35)
                    
                    print('\n  Potencias generadores:')
                    for h in range(ng):
                        clean_name = gen_names[h].replace('.ElmSym', '').replace('.ElmGenstat', '')
                        p_val = p_post.X[h, c_real, w_real]
                        delta = p_val - p_pre.X[h, w_real]
                        signo = "+" if delta >= 0 else ""
                        print(f"    p_post[{h+1:2d}, {clean_name:25s}] = {p_val:7.3f} MW  ({signo}{delta:+6.3f})")
                    
                    print('\n  Energia no suministrada:')
                    ens_total = 0
                    for e in range(nb):
                        ens_val = p_ens_post.X[e, c_real, w_real]
                        if ens_val > 0.001:
                            print(f"    ENS barra {e+1} = {ens_val:.3f} MW")
                        ens_total += ens_val
                    if ens_total < 0.001:
                        print(f"    Total ENS = {ens_total:.6f} MW (cero o despreciable)")
                    else:
                        print(f"    Total ENS = {ens_total:.3f} MW (déficit)")
                    
                    print('\n  Flujos líneas:')
                    for l in range(nl):
                        f_val = f_post.X[l, c_real, w_real]
                        delta_f = f_val - f_pre.X[l, w_real]
                        signo = "+" if delta_f >= 0 else ""
                        print(f"    f_post[{branch_from[l]:2.0f} -> {branch_to[l]:2.0f}] = {f_val:7.3f} MW  ({signo}{delta_f:+6.3f})")
                    
                    ploss_val = ploss_post.X[:, c_real, w_real].sum()
                    delta_loss = ploss_val - ploss_pre.X[:, w_real].sum()
                    signo = "+" if delta_loss >= 0 else ""
                    print(f'\n  Pérdidas totales: {ploss_val:.3f} MW  ({signo}{delta_loss:+.3f})')
    if True:
        print("\n" + "=" * 5 + " Factores de participación " + "=" * 5)

        # === Selector ===
        casos_imprimir = [2]        # casos a imprimir
        escenarios_imprimir = [0]   # índices w a imprimir (0-based)
        conts_imprimir = None       # None = todas, o lista como [0, 1, 5]

        for i, u_val in enumerate(casos_ejecutar):
            if u_val not in casos_imprimir:
                continue

            vars_case = vars_list[i]
            p_pre_val = vars_case['p_pre'].X        # (ng, n_w)
            p_post_val = vars_case['p_post'].X      # (ng, K, n_w)
            contingencias = vars_case['contingencias']
            gen_names = vars_case['gen_names']
            ng = p_pre_val.shape[0]
            idx_erv = range(ng-3,ng)
            K_u = len(contingencias)

            print(f"\n{'='*10} CASO {u_val} {'='*10}")

            for w in escenarios_imprimir:
                print(f"\n  --- Escenario w={w} (eta={eta_list[w]:.3f} MW) ---")

                for k_idx, (tipo, index) in enumerate(contingencias):
                    if conts_imprimir is not None and k_idx not in conts_imprimir:
                        continue

                    # Variación de potencia del sistema P_agc
                    if tipo == 'gen':
                        P_agc = p_pre_val[index - 1, w]
                    elif tipo == 'load':
                        nombre_k = f'Cont{k_idx+1}_load{index}'
                        Load_post = vars_case['Load_bus_post'][nombre_k]
                        Load_pre  = vars_case['Load_bus_pre']
                        if index == 2:
                            P_agc = Load_pre[5] - Load_post[5]
                        elif index == 4:
                            P_agc = Load_pre[1] - Load_post[1]
                        elif index == 11:
                            P_agc = Load_pre[2] - Load_post[2]
                        else:
                            P_agc = Load_pre[7] - Load_post[7]

                    if abs(P_agc) < 1e-4:
                        continue

                    print(f"\n    Cont{k_idx+1} ({tipo} {index}) | P_agc = {P_agc:.3f} MW")

                    gamma_planta_wtg = 0.0
                    delta_planta_wtg = 0.0

                    for h in range(ng):
                        clean_name = gen_names[h].replace('.ElmSym','').replace('.ElmGenstat','')
    
                        # Caso 1: El generador fuera de servicio
                        if tipo == 'gen' and h == index - 1:
                            gamma = 0.0
                            # delta_p será negativo (o cero) mostrando la caída real
                            delta_p = p_post_val[h, k_idx, w] - p_pre_val[h, w] 
                            print(f"      γ[{h+1}, {clean_name}] = {gamma:.4f}  "
                                f"(Δp = {delta_p:+.3f} MW)")
                            # continue aquí para no sumarlo a los acumuladores WTG
                            continue

                        # Caso 2: El resto de los generadores
                        delta_p = p_post_val[h, k_idx, w] - p_pre_val[h, w]
                        gamma = delta_p / P_agc

                        # Solo imprimimos si el factor de participación es significativo
                        if abs(gamma) > 1e-4:
                            print(f"      γ[{h+1}, {clean_name}] = {gamma:.4f}  "
                                f"(Δp = {delta_p:+.3f} MW)")
                            
                        # Acumular WTGs
                        if h in idx_erv:
                            gamma_planta_wtg += gamma
                            delta_planta_wtg += delta_p

                    # Factor de participación de la planta eólica
                    if abs(gamma_planta_wtg) > 1e-4:
                        print(f"      γ[Planta WTG] = {gamma_planta_wtg:.4f}  "
                            f"(Δp total = {delta_planta_wtg:+.3f} MW)")
                    gamma_total = sum(
                        (p_post_val[h, k_idx, w] - p_pre_val[h, w]) / P_agc
                        for h in range(ng)
                        if not (tipo == 'gen' and h == index - 1)
                    )
                    print(f"      Σγ = {gamma_total:.4f} (debería ser ≈ 1)")
                    
elif status == GRB.Status.INF_OR_UNBD or \
    status == GRB.Status.INFEASIBLE  or \
    status == GRB.Status.UNBOUNDED:
    print('The model cannot be solved because it is infeasible or unbounded => status "%d"' % status)
    m.computeIIS()
    m.write("model_iis.ilp")
    print("IIS written to model_iis.ilp")
