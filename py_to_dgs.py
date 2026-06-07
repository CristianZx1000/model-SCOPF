if True:
    print("\n" + "=" * 5 + " Factores de participación " + "=" * 5)

    # === Selector ===
    casos_imprimir = [2]        # casos a imprimir
    escenarios_imprimir = [0]   # índices w a imprimir (0-based)
    conts_imprimir = [1]       # None = todas, o lista como [0, 1, 5]

    for i, u_val in enumerate(casos_ejecutar):
        if u_val not in casos_imprimir:
            continue

        vars_case = vars_list[i]
        p_pre_val = vars_case['p_pre'].X        # (ng, n_w)
        p_post_val = vars_case['p_post'].X      # (ng, K, n_w)
        ploss_pre_val = vars_case['ploss_pre'].X # (nl, n_w)
        ploss_post_val = vars_case['ploss_post'].X # (nl, K, n_w)

        contingencias = vars_case['contingencias']
        gen_names = vars_case['gen_names']
        ng = p_pre_val.shape[0]
        idx_erv = range(ng-3,ng)
        K_u = len(contingencias)

        # Identificar los índices locales y nombres ordenados según gen_agc
        idx_agc = []
        nombres_agc = []
        for name in gen_agc:
            matches = [h for h, full_name in enumerate(gen_names) if name in full_name]
            if matches:
                idx_agc.append(matches[0])
                nombres_agc.append(name)

        print(f"\n{'='*10} CASO {u_val} {'='*10}")

        for w in escenarios_imprimir:
            print(f"\n  --- Escenario w={w} (eta={eta_list[w]:.3f} MW) ---")

            for k_idx, (tipo, index) in enumerate(contingencias):
                if conts_imprimir is not None and k_idx not in conts_imprimir:
                    continue

                # Variación de potencia del sistema P_agc
                if tipo == 'gen':
                    delta_loss = ploss_post_val[:, k_idx, w].sum() - ploss_pre_val[:, w].sum()
                    if index-1 in idx_erv:
                        P_agc = p_pre_val[index - 1, w] + eta_list[w] + delta_loss
                    else:
                        P_agc = p_pre_val[index - 1, w] + delta_loss

                elif tipo == 'load':
                    nombre_k = f'Cont{k_idx+1}_load{index}'
                    Load_post = vars_case['Load_bus_post'][nombre_k]
                    Load_pre  = vars_case['Load_bus_pre']
                    if index == 2:
                        delta_load = Load_post[5] - Load_pre[5]
                    elif index == 4:
                        delta_load = Load_post[1] - Load_pre[1]
                    elif index == 11:
                        delta_load = Load_post[2] - Load_pre[2]
                    else:
                        delta_load = Load_post[7] - Load_pre[7]

                    delta_loss = ploss_post_val[:, k_idx, w].sum() - ploss_pre_val[:, w].sum()
                    P_agc = delta_load + delta_loss

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
                        delta_p = p_post_val[h, k_idx, w] - p_pre_val[h, w]
                        # Solo imprimir si está en AGC
                        if h in idx_agc:
                            print(f"      γ[{h+1}, {clean_name}] = {gamma:.4f}  "
                            f"(Δp = {delta_p:+.3f} MW)")
                        # continue aquí para no sumarlo a los acumuladores WTG
                        continue

                    # Caso 2: El resto de los generadores
                    delta_p = p_post_val[h, k_idx, w] - p_pre_val[h, w]
                    gamma = delta_p / P_agc

                    # Solo imprimimos si el factor de participación es significativo y el gen. está en AGC
                    if abs(gamma) > 1e-4 and h in idx_agc:
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

import mod_pa as mpa

if True:
    if True:
        # Seleccionar el escenario
        nombre_escenario = "CASO 3"
        escenario = prj.GetContents(nombre_escenario, 1)[0]
        escenario.Activate()

    # Asignar estatismo a control de planta WTGs y potencia max a control PQ WTGs
    R = 2
    p_max = 0.9
    on_off = True

    mpa.mod_pe(R, p_max, on_off)

    app.Show() # abrir pf en Modo Engine

    if True:
        # Enviar resultados a PowerFactory
        for h, gen_name in enumerate(gen_names):
            gen_obj = app.GetCalcRelevantObjects(gen_name)[0]
            
            # Asignar potencia activa
            gen_obj.pgini = float(p_pre[h].X)

            print(f"Asignado {p_pre[h].X:.3f} MW a {gen_name}")

            # Asignar factor de participación
            
            for i in range(1,4):
                app.DefineTransferAttributes(f'ElmDsl', 'e:params:gamma{i}')
                agc_obj = app.GetCalcRelevantObjects('AGC controller.ElmDsl')[0]
                # Pasa el valor como lista si es solo un atributo
                agc_obj.SetAttributes([gamma])
                app.PrintInfo(f"Parámetro gamma{i} modificado a {gamma} en AGC")
