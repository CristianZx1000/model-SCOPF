import sys, os
import time
import numpy as np
import pandas as pd
from io import StringIO

os.environ["PATH"] = r"D:\Program Files\DIgSILENT\PowerFactory 2024" + os.environ["PATH"]
sys.path.append(r"D:\Program Files\DIgSILENT\PowerFactory 2024\Python\3.9")
import powerfactory

app = powerfactory.GetApplication()
app.Show()

NOMBRE_PROYECTO = 'BD SM Punta Arenas 2023 estocastico'  # ajusta si el nombre real difiere
project = app.ActivateProject(NOMBRE_PROYECTO)
prj = app.GetActiveProject()
print(f"Proyecto activo: {prj.loc_name if prj else 'ERROR'}")

# =========================================================
# Configuración de nombres y elementos
# =========================================================
UNIDAD_U4 = "Maestro Tres Puentes #4.ElmComp"
UNIDAD_U8 = "Maestro Tres Puentes #8.ElmComp"
UNIDAD_U9 = "Maestro Tres Puentes #9.ElmComp"

UNIDAD_U4_SYM = "Unidad Nº 4 Solar Mars.ElmSym"
UNIDAD_U8_SYM = "Unidad Nº 8 GE10.ElmSym"
UNIDAD_U9_SYM = "Unidad Nº 9 Solar Titan.ElmSym"

CONTINGENCIA_GENERADOR = "Unidad Nº 7 Solar Titan.ElmSym"
CONTINGENCIA_CARGA     = "Alimentador 04.ElmLod"

BARRA_FRECUENCIA = "Barra Principal de 13.2 kV.ElmTerm"
NOMBRE_PPC_DSL = "Control de Planta.ElmDsl"
NOMBRE_MATRIZ_PVSF = "PvsF.IntMat"

TIEMPO_EVENTO = 1  # según tu código de referencia; cambia a 0 si prefieres consistencia con el caso único
USAR_CHEQUEO_MODAL = False

ESCENARIOS_ESTOCASTICOS = ["CASO 1", "CASO 2", "CASO 4", "CASO 5", "CASO 6"]
Ws = 1 / len(ESCENARIOS_ESTOCASTICOS)

# --- Grupo maestro: unión de unidades controlables + PE ---
# (nombre_grupo, ElmComp, ElmSym, bounds)
MASTER_GRUPOS = [
    ("U4", UNIDAD_U4, UNIDAD_U4_SYM, [(0, 0.1), (0, 20), (0, 10), (0, 20)]),
    ("U9", UNIDAD_U9, UNIDAD_U9_SYM, [(0, 0.1), (0, 20), (0, 10), (0, 20)]),
    ("U8", UNIDAD_U8, UNIDAD_U8_SYM, [(0, 0.1), (0, 20), (0, 10), (0, 20)]),
    ("PE", None, None, [(2, 8), (10, 30), (5, 15)]),
]
bounds = [b for _, _, _, bg in MASTER_GRUPOS for b in bg]
print(f"Total de parámetros a optimizar: {len(bounds)}")


def generar_matriz_estatismo(R, f_nominal=50.0, banda_muerta=0.4, P_max=1.0, P_min=-1.0):
    delta_f_pu_max = (P_max * R) / 100
    delta_f_Hz_max = delta_f_pu_max * f_nominal
    f_min = f_nominal - abs(delta_f_Hz_max)
    f_bd_inferior = f_nominal - banda_muerta / 2
    f_bd_superior = f_nominal + banda_muerta / 2
    f_antes_bd_inf = f_bd_inferior - 0.01
    delta_f_pu_antes = (f_nominal - f_antes_bd_inf) / f_nominal
    P_antes_bd_inf = (delta_f_pu_antes / R) * 100
    f_intermedio_bajo = (f_min + f_antes_bd_inf) / 2
    delta_f_pu_int_bajo = (f_nominal - f_intermedio_bajo) / f_nominal
    P_intermedio_bajo = (delta_f_pu_int_bajo / R) * 100
    return [
        [f_min, P_max], [f_intermedio_bajo, P_intermedio_bajo],
        [f_antes_bd_inf, P_antes_bd_inf], [f_bd_inferior, 0.0],
        [f_nominal, 0.0], [f_bd_superior, 0.0],
        [51.5, -0.715], [51.99, -0.715], [52, P_min]
    ]


def actualizar_matriz_dinamica(app, estatismo, verbose=False):
    nueva_matriz = generar_matriz_estatismo(estatismo)
    ppc_dsl = app.GetCalcRelevantObjects(NOMBRE_PPC_DSL)[0]
    matriz_pvsf = ppc_dsl.GetContents(NOMBRE_MATRIZ_PVSF)[0]
    matriz_pvsf.Init(len(nueva_matriz), len(nueva_matriz[0]))
    for i, fila in enumerate(nueva_matriz):
        for j, val in enumerate(fila):
            matriz_pvsf.Set(i + 1, j + 1, val)
    if verbose:
        print(f"Matriz PvsF actualizada (estatismo={estatismo}%)")


def check_modal(app):
    comMod = app.GetFromStudyCase("ComMod")
    comMod.iopt_met, comMod.initMode = 0, 0
    if comMod.Execute() != 0:
        return False
    comMod.ResultFile.Load()
    col = comMod.ResultFile.FindColumn("b:eigvalr")
    _, maxRealPart = comMod.ResultFile.FindMaxInColumn(col)
    return maxRealPart >= 0


def simular_escenario(app, x, nombre_escenario, indicador="ISE", verbose=True):
    """Corre la simulación completa para UN escenario y devuelve su índice (o penalización)."""
    PENALTY_MODAL_END, PENALTY_EVT_STOP = 6e10, 4e10
    PENALTY_FAIL, PENALTY_CV = 1e10, 5e9

    escenario = project.GetContents(nombre_escenario, 1)[0]
    escenario.Activate()

    try:
        app.GetActiveProject().Purge()
        for ev in app.GetFromStudyCase("Simulation Events/Fault.IntEvt").GetContents():
            ev.Delete()
    except:
        pass

    # --- Aplicar parámetros por grupo, solo si la unidad está en servicio en ESTE escenario ---
    idx = 0
    try:
        app.DefineTransferAttributes("ElmDsl", "e:params:Kdroop,e:params:Kp,e:params:Ki,e:params:Kd")
        for nombre_grupo, nombre_comp, nombre_sym, bounds_grupo in MASTER_GRUPOS:
            n_params = len(bounds_grupo)
            valores = x[idx: idx + n_params]
            idx += n_params

            if nombre_grupo == "PE":
                actualizar_matriz_dinamica(app, valores[0], verbose=False)
                app.DefineTransferAttributes("ElmDsl", "e:params:Kp_p,e:params:Ki_p")
                ppc = app.GetCalcRelevantObjects(NOMBRE_PPC_DSL)[0]
                ppc.SetAttributes([valores[1], valores[2]])
                continue

            obj_sym = app.GetCalcRelevantObjects(nombre_sym)
            if not obj_sym or obj_sym[0].outserv == 1:
                continue  # unidad no participa en este escenario

            comp = app.GetCalcRelevantObjects(nombre_comp)[0]
            comp.SearchObject("GASTWD").SetAttributes(list(valores))

    except Exception as e:
        if verbose: print(f"  [{nombre_escenario}] Error aplicando parámetros: {e}")
        return PENALTY_FAIL

    # --- Contingencia según tipo de escenario ---
    if nombre_escenario in ["CASO 1", "CASO 2", "CASO 4", "CASO 5"]:
        nombre_contingencia = CONTINGENCIA_GENERADOR
    else:
        nombre_contingencia = CONTINGENCIA_CARGA

    event = None
    ffx = PENALTY_FAIL
    try:
        simulationEvents = app.GetActiveStudyCase().GetContents("Simulation Events/Fault.IntEvt")[0]
        allCalculations = app.GetActiveStudyCase().GetContents("All calculations.ElmRes")[0]

        obj_contingencia = app.GetCalcRelevantObjects(nombre_contingencia)[0]
        event = simulationEvents.CreateObject("EvtSwitch", f"evento_{nombre_escenario}")
        event.p_target = obj_contingencia
        event.time = TIEMPO_EVENTO

        comInc = app.GetFromStudyCase("ComInc")
        comInc.p_event, comInc.p_resvar = simulationEvents, allCalculations
        if comInc.Execute() != 0:
            raise RuntimeError("Fallo ComInc")

        penalty_flag = None
        if USAR_CHEQUEO_MODAL and check_modal(app):
            penalty_flag = 8e10  # PENALTY_MODAL inicial

        busFreq = app.GetCalcRelevantObjects(BARRA_FRECUENCIA)[0]
        allCalculations.AddVariable(busFreq, "m:fehz")
        allGens = app.GetCalcRelevantObjects("*.ElmSym")

        comres = app.GetFromStudyCase("ComRes")
        resultobj_list = [allCalculations, allCalculations]
        element_list = [allCalculations, busFreq]
        cvariable_list = ["b:tnow", "m:fehz"]
        gen_names_exported = []

        for gen in allGens:
            if gen.outserv != 1:
                allCalculations.AddVariable(gen, "s:xspeed")
                if gen.loc_name != obj_contingencia.loc_name:
                    resultobj_list.append(allCalculations)
                    element_list.append(gen)
                    cvariable_list.append("s:xspeed")
                    gen_names_exported.append(gen.loc_name)

        comSim = app.GetFromStudyCase("ComSim")
        comSim.tstop = 30
        if comSim.Execute() != 0:
            raise RuntimeError("Fallo ComSim")

        if USAR_CHEQUEO_MODAL and check_modal(app):
            penalty_flag = PENALTY_MODAL_END

        archivo = os.path.join(os.getcwd(), f"Results_{nombre_escenario.replace(' ', '_')}.txt")
        comres.f_name = archivo
        comres.iopt_exp, comres.iopt_csel = 4, 1
        comres.resultobj, comres.element, comres.cvariable = resultobj_list, element_list, cvariable_list
        if comres.Execute() != 0:
            raise RuntimeError("Fallo ComRes")

        out_win = app.GetOutputWindow()
        msgs_plain = out_win.GetContent(out_win.MessageType.Plain)
        if any("EvtStop" in m for m in msgs_plain):
            penalty_flag = PENALTY_EVT_STOP

        with open(archivo, "r", encoding="latin-1") as f:
            contenido = f.read()
        df_raw = pd.read_csv(StringIO(contenido), header=None, delimiter="\t", decimal=",")
        df = df_raw.apply(pd.to_numeric, errors="coerce").dropna()
        Values_fit = df.values[df.values[:, 0] >= 0]

        if len(Values_fit) > 5:
            X = Values_fit[:, 0]
            integra = getattr(np, "trapezoid", getattr(np, "trapz"))
            fr_err = np.abs(Values_fit[:, 1] - 50)
            indices = {
                "ITAE": integra(fr_err * X, x=X),
                "IAE":  integra(fr_err, x=X),
                "ITSE": integra((fr_err ** 2) * X, x=X),
                "ISE":  integra((fr_err ** 2), x=X),
            }
            iae_xspeed_list = []
            for i, gen_name in enumerate(gen_names_exported):
                col_idx = i + 2
                if col_idx < Values_fit.shape[1]:
                    spd_err = np.abs(Values_fit[:, col_idx] - 1.0)
                    iae_xspeed_list.append(integra(spd_err, x=X))

            if penalty_flag is None and iae_xspeed_list:
                cv = np.std(iae_xspeed_list) / np.mean(iae_xspeed_list)
                if cv > 0.02:
                    penalty_flag = PENALTY_CV

            ffx = penalty_flag if penalty_flag else indices.get(indicador, PENALTY_FAIL)
        else:
            ffx = penalty_flag if penalty_flag else PENALTY_FAIL

    except Exception as e:
        if verbose: print(f"  [{nombre_escenario}] Error simulación: {e}")
        ffx = PENALTY_FAIL
    finally:
        try:
            app.GetFromStudyCase("ComLdf").Execute()
            if event: event.Delete()
            app.GetOutputWindow().Clear()
        except:
            pass

    if verbose:
        print(f"  [{nombre_escenario}] {indicador} = {ffx:.4f}")
    return float(ffx)


def OF(app, x, indicador="ISE"):
    """Función objetivo estocástica: promedio ponderado sobre los 5 escenarios."""
    t_inicio = time.time()

    if len(x) != len(bounds) or any(val < lb or val > ub for val, (lb, ub) in zip(x, bounds)):
        return float(1e11)

    valores_por_escenario = [simular_escenario(app, x, esc, indicador=indicador) for esc in ESCENARIOS_ESTOCASTICOS]
    FO_total = sum(Ws * v for v in valores_por_escenario)

    try:
        historial_file = os.path.join(os.getcwd(), f"{indicador}_estocastico_historial.txt")
        if not os.path.exists(historial_file):
            with open(historial_file, "w") as f:
                f.write("Iteracion\tFO_total\t" + "\t".join(ESCENARIOS_ESTOCASTICOS) + "\tTiempo_s\tParametros\n")
        iteracion = len(open(historial_file).readlines())
        with open(historial_file, "a") as h:
            h.write(f"{iteracion}\t{FO_total:.6f}\t" +
                    "\t".join(f"{v:.6f}" for v in valores_por_escenario) +
                    f"\t{time.time() - t_inicio:.2f}\t" +
                    "\t".join(f"{v:.12f}" for v in x) + "\n")
    except:
        pass

    print(f"[OF estocástico] FO_total={FO_total:.4f} | escenarios={[f'{v:.2f}' for v in valores_por_escenario]} | tiempo={time.time()-t_inicio:.1f}s")
    return float(FO_total)


# =========================================================
# Prueba manual (recomendado ANTES de lanzar Optuna con muchos trials)
# =========================================================
x0 = [
    0.0209, 5, 0.7, 5,      # U4
    0.0344, 10, 1, 0,       # U9
    0.05, 10, 0.1, 1,       # U8
    2, 20, 10,              # Parque eólico: Estatismo, Kp_p, Ki_p
]
assert len(x0) == len(bounds), "Descoordinación entre x0 y bounds"

app.Show()
valor_prueba = OF(app, x0, "ISE")
print(f"FO estocástica de prueba: {valor_prueba}")


# =========================================================
# Optimización con Optuna
# =========================================================
import optuna

app.Hide()

def objective(trial):
    x = []
    for nombre_grupo, _, _, bounds_grupo in MASTER_GRUPOS:
        for i, (lb, ub) in enumerate(bounds_grupo):
            x.append(trial.suggest_float(f"{nombre_grupo}_p{i}", lb, ub))
    return OF(app, x, "ISE")

def build_dict_from_list(x_list):
    d = {}
    idx = 0
    for nombre_grupo, _, _, bounds_grupo in MASTER_GRUPOS:
        for i in range(len(bounds_grupo)):
            d[f"{nombre_grupo}_p{i}"] = x_list[idx]
            idx += 1
    return d

seed_params = build_dict_from_list(x0)

study = optuna.create_study(
    direction="minimize",
    sampler=optuna.samplers.TPESampler(multivariate=True),
    study_name="Optimizacion_ISE_Estocastico"
)
study.enqueue_trial(seed_params)

N_TRIALS = 3  # sube gradualmente; cada trial corre 5 simulaciones completas
study.optimize(objective, n_trials=N_TRIALS)

print(f"\nMejor FO estocástica: {study.best_value}")
print("Mejores parámetros:", study.best_params)

# --- Reconstruir x_opt y verificar ---
def build_x_from_best_params(best_params):
    x = []
    for nombre_grupo, _, _, bounds_grupo in MASTER_GRUPOS:
        for i in range(len(bounds_grupo)):
            x.append(best_params[f"{nombre_grupo}_p{i}"])
    return x

x_opt = build_x_from_best_params(study.best_params)
app.Show()
valor_verificado = OF(app, x_opt, "ISE")
print(f"Verificación x_opt: {valor_verificado}")
print(f"x_opt = {x_opt}")

df_hist = study.trials_dataframe()
df_hist.to_csv("historial_completo_optuna_estocastico.csv", index=False)
