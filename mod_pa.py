# # Enlazar python con PowerFactory # llamar al sistema operativo
# import os;
# os.environ["PATH"]=r"D:\Program Files\DIgSILENT\PowerFactory 2021 SP2"+os.environ["PATH"]

# # Importar la aplicación # tener acceso desde la ruta donde esta powerfactory
# import sys
# sys.path.append(r"D:\Program Files\DIgSILENT\PowerFactory 2021 SP2\Python\3.9")

# # Importar la aplicación # importar el módulo que da acceso a la aplicación
# import powerfactory as pf

# app=pf.GetApplication()
# app.Show() # abrir pf en Modo Engine
 
# # Activar el proyecto
# user =app.GetCurrentUser()                # abre el usuario
# project=app.ActivateProject('BD SM Punta Arenas 2023 ECF y EDAC') # abre el archivo pfd
# prj = app.GetActiveProject()              # activar el proyecto

# # Seleccionar el escenario
# nombre_escenario = "CASO 3"
# escenario = prj.GetContents(nombre_escenario, 1)[0]
# escenario.Activate()

#import powerfactory as pf
# app = pf.GetApplication()

# Desactivar controles (Obtener caso base)
def activar_control(on_off, app):
    if on_off:
    # Desactivar controles (Obtener caso base)
    ppc = app.GetCalcRelevantObjects('Control de Planta PE Cabo Negro.ElmComp')[0]
    ppc.SetAttribute('outserv', 1)
    
    for i in range(1,4):
        wtg = app.GetCalcRelevantObjects(f'Control_WTG{i}.ElmComp')[0]    
        wtg.SetAttribute('outserv', 1)
    else:
    #Activar controles
    ppc = app.GetCalcRelevantObjects('Control de Planta PE Cabo Negro.ElmComp')[0]
    ppc.SetAttribute('outserv', 0)
    
    for i in range(1,4):
        wtg = app.GetCalcRelevantObjects(f'Control_WTG{i}.ElmComp')[0]    
        wtg.SetAttribute('outserv', 0)

#################################################################
# Modificación de controladores 
def mod_control(nuevo_pmax, app):
    # Modificar el parametro Pmax en los controladores eléctricos
    app.DefineTransferAttributes('ElmDsl', 'e:params:Pmax')

    # Modificar el parámetro Pmax en cada control
    for i in range(1,4):
        wtg_control = app.GetCalcRelevantObjects(f'Control Eléctrico WTG{i}.ElmDsl')[0]
        # Pasa el valor como lista si es solo un atributo
        wtg_control.SetAttributes([nuevo_pmax])
        app.PrintInfo(f"Parámetro Pmax modificado a {nuevo_pmax} en Control Eléctrico WTG{i}")

#################################################################
# Crear matrices PvsF
def generar_matriz_estatismo(R, f_nominal=50.0, banda_muerta=0.2*2, P_max=1.0, P_min=-1.0):
    """
    Genera una matriz PvsF basada en el estatismo R.
    
    Parámetros:
    - R: Estatismo en porcentaje (1, 2, 3, 4, 5, etc.)
    - f_nominal: Frecuencia nominal en Hz (default: 50.0)
    - banda_muerta: Ancho de la banda muerta en Hz (default: 0.1)
    - P_max: Potencia máxima en p.u. (default: 1.0)
    - P_min: Potencia mínima en p.u. (default: -1.0)
    
    Retorna:
    - Lista de listas con formato [[f1, P1], [f2, P2], ...]
    
    Fórmula del estatismo:
    R = (Δf_pu / ΔP) * 100
    donde Δf_pu = Δf_Hz / f_nominal
    
    Despejando:
    Δf_Hz = (ΔP * R * f_nominal) / 100
    """
    
    # Calcular el rango de frecuencia necesario para alcanzar P_max y P_min
    # Δf_pu = (ΔP * R) / 100
    # Δf_Hz = Δf_pu * f_nominal
    
    delta_f_pu_max = (P_max * R) / 100  # Variación de frecuencia en p.u. para P_max
    delta_f_pu_min = (P_min * R) / 100  # Variación de frecuencia en p.u. para P_min
    
    # Convertir a Hz
    delta_f_Hz_max = delta_f_pu_max * f_nominal  # En Hz
    delta_f_Hz_min = delta_f_pu_min * f_nominal  # En Hz
    
    # Límites de frecuencia
    # Para P_max (positivo), la frecuencia debe estar por debajo de f_nominal
    f_min = f_nominal - abs(delta_f_Hz_max)  
    # Para P_min (negativo), la frecuencia debe estar por encima de f_nominal
    f_max = f_nominal + abs(delta_f_Hz_min)  
    
    # Calcular límites de banda muerta
    f_bd_inferior = f_nominal - banda_muerta / 2
    f_bd_superior = f_nominal + banda_muerta / 2
    
    # Punto justo antes de entrar a banda muerta (inferior)
    f_antes_bd_inf = f_bd_inferior - 0.01
    delta_f_pu_antes = (f_nominal - f_antes_bd_inf) / f_nominal
    P_antes_bd_inf = (delta_f_pu_antes / R) * 100
    
    # Punto justo después de salir de banda muerta (superior)
    f_despues_bd_sup = f_bd_superior + 0.01
    delta_f_pu_despues = (f_nominal - f_despues_bd_sup) / f_nominal
    P_despues_bd_sup = (delta_f_pu_despues / R) * 100
    
    # Puntos intermedios para suavizar la curva
    f_intermedio_bajo = (f_min + f_antes_bd_inf) / 2
    delta_f_pu_int_bajo = (f_nominal - f_intermedio_bajo) / f_nominal
    P_intermedio_bajo = (delta_f_pu_int_bajo / R) * 100
    
    f_intermedio_alto = (f_despues_bd_sup + f_max) / 2
    delta_f_pu_int_alto = (f_nominal - f_intermedio_alto) / f_nominal
    P_intermedio_alto = (delta_f_pu_int_alto / R) * 100
    
    # Construir la matriz
    matriz = [
        [f_min, P_max],
        [f_intermedio_bajo, P_intermedio_bajo],
        [f_antes_bd_inf, P_antes_bd_inf],
        [f_bd_inferior, 0.0],
        [f_nominal, 0.0],
        [f_bd_superior, 0.0],
        [f_despues_bd_sup, P_despues_bd_sup],
        [f_intermedio_alto, P_intermedio_alto],
        [f_max, P_min],
    ]
    
    return matriz


def actualizar_matriz_dinamica(estatismo, app):
    """
    Actualiza la matriz PvsF generándola dinámicamente según el estatismo.
    """
    # Generar la matriz
    nueva_matriz = generar_matriz_estatismo(estatismo)
    
    n_filas_nueva = len(nueva_matriz)
    n_columnas_nueva = len(nueva_matriz[0])

    # Obtener el control
    ppc_control = app.GetCalcRelevantObjects('Control de Planta.ElmDsl')[0]
    matriz_pvsf = ppc_control.GetContents('PvsF.IntMat')[0]
        
    # Redimensionar la matriz antes de rellenar
    matriz_pvsf.Init(n_filas_nueva, n_columnas_nueva)
    
    # Asignar valores: Reemplazar elemento a elemento
    for i in range(n_filas_nueva):
        for j in range(n_columnas_nueva):
            matriz_pvsf.Set(i + 1, j + 1, nueva_matriz[i][j])
    
    # Mostrar la nueva matriz
    print("-" * 50) 
    print(f"Matriz PvsF generada para estatismo {estatismo}% ({n_filas_nueva} x {n_columnas_nueva}):")
    titulo = ["f (Hz)", "DP (p.u.)"]
    print(" | ".join(titulo))
    for i in range(1, n_filas_nueva + 1):
        fila = []
        for j in range(1, n_columnas_nueva + 1):
            valor = matriz_pvsf.Get(i, j)
            fila.append(f"{valor:.4f}")
        print(" | ".join(fila))
    
    print("-" * 50)

def mod_pe(R, p_max, on_off, app):
    activar_control(on_off, app)
    mod_control(p_max, app)
    actualizar_matriz_dinamica(R, app)
