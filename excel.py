from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
import pandas as pd
import os

# ==== Exportar a Excel ====
nombre_archivo = "resultados_paper_escenarios.xlsx"

# Calcular componentes del costo total
Cop_pre_val = sum(
    (a_g @ p_pre[:, w].X + b_g.sum() + Cto_ens * p_ens_pre[:, w].X.sum()) / n_w
    for w in range(n_w)
)

Cop_post_val = sum(
    (a_g @ p_post[:, k, w].X + b_g.sum() + Cto_ens * p_ens_post[:, k, w].X.sum()) / (n_w * K) # k
    for w in range(n_w)
    for k in range(K)
)

C_res_val = sum(Cto_up[g] * r_up.X[g] + Cto_dn[g] * r_dn.X[g] for g in range(ng))

# ==== Crear una hoja por cada escenario ====
with pd.ExcelWriter(nombre_archivo, engine="openpyxl") as writer:
    
    # Iterar sobre TODOS los escenarios
    for w_idx in range(n_w):
        eta_val = eta_list[w_idx]
        nombre_hoja = f"eta_{int(eta_val)}"
        
        # ----------------------------------------
        # 1. Tabla precontingencia (generación)
        # ----------------------------------------
        datos_pre = []
        for h in range(ng):
            datos_pre.append({
                "Generador": h+1,
                "Potencia pre (MW)": round(p_pre.X[h, w_idx], 3),
                "Reserva Up (MW)": round(r_up.X[h], 3),
                "Reserva Dn (MW)": round(r_dn.X[h], 3)
            })
        tabla_pre = pd.DataFrame(datos_pre)
        
        # ----------------------------------------
        # 2. Tabla postcontingencia (generación)
        # ----------------------------------------
        datos_post = {"Generador\ contingencia": [h+1 for h in range(ng)]}
        for c in range(K):
            tipo, idx = contingencias[c]
            #nombre_col = f"k{c+1}: {tipo}{idx}"
            if tipo == "gen":
                nombre_col = f"Cont{c+1}: gen. {idx}"
            elif tipo == "line":
                nombre_col = f"Cont{c+1}: línea {int(sep['branch'][idx-1,0])}-{int(sep['branch'][idx-1,1])}"
            else:
                nombre_col = f"Cont{c+1}: {tipo}{idx}"
            datos_post[nombre_col] = [round(p_post.X[h, c, w_idx], 3) for h in range(ng)]
        tabla_post = pd.DataFrame(datos_post)

        # ----------------------------------------
        # 3. Tabla ENS (corte de carga)
        # ----------------------------------------
        datos_ens = []
        umbral_cero = 1e-5
        for b in range(nb):
            # Extraer valores para verificar si hay ENS en esta barra
            valor_pre = round(float(p_ens_pre.X[b, w_idx]), 3)
            valores_post = [round(float(p_ens_post[b, c, w_idx].X), 3) for c in range(K)]

            # Condición: ¿Existe algún valor mayor a cero en pre o en cualquier contingencia?
            if valor_pre > umbral_cero or any(v > umbral_cero for v in valores_post):
                fila_ens = {
                    "Bus": b+1, 
                    "ENS Pre": valor_pre #round(p_ens_pre.X[b, w_idx], 3)
                }
                
                for c in range(K):
                    tipo, idx = contingencias[c]
                    #nombre_col = f"k{c+1}: {tipo}{idx}"
                    if tipo == "gen":
                        nombre_col = f"Cont{c+1}: gen. {idx}"
                    elif tipo == "line":
                        nombre_col = f"Cont{c+1}: línea {int(sep['branch'][idx-1,0])}-{int(sep['branch'][idx-1,1])}"
                    else:
                        nombre_col = f"Cont{c+1}: {tipo}{idx}"
                    fila_ens[nombre_col] = valores_post[c] #round(p_ens_post.X[b, c, w_idx], 3)
            
                datos_ens.append(fila_ens)
            
        tabla_ens = pd.DataFrame(datos_ens)
        
        # ----------------------------------------
        # 4. Tabla flujos (pre + post)
        # ----------------------------------------
        # datos_flujos = {
        #     "Línea\ contingencia": [f"{int(sep['branch'][l,0])}-{int(sep['branch'][l,1])}" for l in range(nl)],
        #     "Flujo pre (MW)": [round(f_pre.X[l, w_idx], 3) for l in range(nl)]
        # }
        # for c in range(K):
        #     tipo, idx = contingencias[c]
        #     #nombre_col = f"k{c+1}: {tipo}{idx}"
        #     if tipo == "gen":
        #         nombre_col = f"Cont{c+1}: gen. {idx}"
        #     elif tipo == "line":
        #         nombre_col = f"Cont{c+1}: línea {int(sep['branch'][idx-1,0])}-{int(sep['branch'][idx-1,1])}"
        #     else:
        #         nombre_col = f"Cont{c+1}: {tipo}{idx}"
        #     datos_flujos[nombre_col] = [round(f_post.X[l, c, w_idx], 3) for l in range(nl)]
        # tabla_flujos = pd.DataFrame(datos_flujos)
        
        # ----------------------------------------
        # 4. Tabla flujos precontingencia
        # ----------------------------------------
        datos_flujos_pre = {
            "Línea": [f"{int(sep['branch'][l,0])}-{int(sep['branch'][l,1])}" for l in range(nl)],
            "Flujo pre (MW)": [round(f_pre.X[l, w_idx], 3) for l in range(nl)]
        }
        tabla_flujos_pre = pd.DataFrame(datos_flujos_pre)

        # ----------------------------------------
        # 5. Tabla flujos POST-contingencia
        # ----------------------------------------
        datos_flujos_post = {
            "Línea \ contingencia": [f"{int(sep['branch'][l,0])}-{int(sep['branch'][l,1])}" for l in range(nl)]
        }
        for c in range(K):
            tipo, idx = contingencias[c]
            if tipo == "gen":
                nombre_col = f"Cont{c+1}: gen. {idx}"
            elif tipo == "line":
                nombre_col = f"Cont{c+1}: línea {int(sep['branch'][idx-1,0])}-{int(sep['branch'][idx-1,1])}"
            else:
                nombre_col = f"Cont{c+1}: {tipo}{idx}"
            
            datos_flujos_post[nombre_col] = [round(f_post.X[l, c, w_idx], 3) for l in range(nl)]
            
        tabla_flujos_post = pd.DataFrame(datos_flujos_post)
        
        # ----------------------------------------
        # Escribir las tablas en la hoja
        # ----------------------------------------
        fila_actual = 0
        
        # 1. Generación pre
        tabla_pre.to_excel(writer, sheet_name=nombre_hoja, index=False, startrow=fila_actual)
        fila_actual += len(tabla_pre) + 2
        
        # 2. Generación post
        tabla_post.to_excel(writer, sheet_name=nombre_hoja, index=False, startrow=fila_actual)
        fila_actual += len(tabla_post) + 2
        
        # 3. ENS
        if not tabla_ens.empty:
            tabla_ens.to_excel(writer, sheet_name=nombre_hoja, index=False, startrow=fila_actual)
            fila_actual += len(tabla_ens) + 2
        
        # 4. Flujos (pre + post)
        #tabla_flujos.to_excel(writer, sheet_name=nombre_hoja, index=False, startrow=fila_actual)

        # 4. Flujos pre
        tabla_flujos_pre.to_excel(writer, sheet_name=nombre_hoja, index=False, startrow=fila_actual)
        fila_actual += len(tabla_flujos_pre) + 2

        # 5. Flujos post
        tabla_flujos_post.to_excel(writer, sheet_name=nombre_hoja, index=False, startrow=fila_actual)

# ==== Agregar resumen de costos y formato ====
wb = load_workbook(nombre_archivo)

for w_idx in range(n_w):
    eta_val = eta_list[w_idx]
    nombre_hoja = f"eta_{int(eta_val)}"
    ws = wb[nombre_hoja]
    
    # Calcular costos específicos del escenario w
    Cop_pre_w = (a_g @ p_pre[:, w_idx].X + b_g.sum() + 
                 Cto_ens * p_ens_pre[:, w_idx].X.sum())
    
    Cop_post_w = sum(
        (a_g @ p_post[:, k, w_idx].X + b_g.sum() + Cto_ens * p_ens_post[:, k, w_idx].X.sum()) / K
        for k in range(K)
    )
    
    # Calcular fila resumen automáticamente buscando la última fila con datos
    fila_resumen = ws.max_row + 2
    
    # Agregar información del escenario
    ws.cell(row=fila_resumen, column=1, value=f"Escenario: eta = {eta_val:.3f} MW, error = {epsilon_list[w_idx]:.3f} MW")
    ws.cell(row=fila_resumen + 1, column=1, value=f"P_fore = {p_fore:.3f} MW, P_VUL = {p_VUL:.3f} MW")
    
    fila_resumen += 3
    
    # Agregar resumen de costos
    ws.cell(row=fila_resumen, column=1, value="Resumen de costos ($/h)")
    ws.cell(row=fila_resumen + 1, column=1, value="Costo total del sistema")
    ws.cell(row=fila_resumen + 1, column=2, value=round(m.objVal, 3))
    
    ws.cell(row=fila_resumen + 2, column=1, value=f"Costo precontingencia (escenario w={w_idx+1})")
    ws.cell(row=fila_resumen + 2, column=2, value=round(Cop_pre_w, 3))
    
    ws.cell(row=fila_resumen + 3, column=1, value="Costo de reserva (total)")
    ws.cell(row=fila_resumen + 3, column=2, value=round(C_res_val, 3))
    
    ws.cell(row=fila_resumen + 4, column=1, value=f"Costo postcontingencia (escenario w={w_idx+1})")
    ws.cell(row=fila_resumen + 4, column=2, value=round(Cop_post_w, 3))
    
    # --- Ajustar ancho de columnas ---
    for col in ws.columns:
        max_length = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                if cell.value:
                    val_len = len(str(cell.value))
                    if val_len > max_length: max_length = val_len
            except:
                pass
        adjusted_width = max_length + 2
        ws.column_dimensions[col_letter].width = adjusted_width

wb.save(nombre_archivo)
print(f"\nResultados exportados a: {nombre_archivo}")
print(f"Hojas creadas: {[sheet for sheet in wb.sheetnames]}")

# ==== Abrir el archivo automáticamente ====
os.startfile(nombre_archivo)
print(f"Abriendo {nombre_archivo}...")
