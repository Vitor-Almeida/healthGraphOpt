import pyomo.environ as pyo
from utils import time_delta
from load_data import load_data
import pandas as pd
from tqdm.auto import tqdm
from datetime import datetime
from unitTest import testing

initialTime=20210401
durationTime=60

#fazer simulação de 14 / 14 dias.

#20:41 começo 120
#xxxxx fim 120 = 15.154.080

#5h => 60, 7mio

#colocar ida e volta

patTypeList,areaIdList,hosIdList,equipTypeList,tList,Demandpat,CONCapacityrht,InitPatientsph,releasePatientspht,LOSp,Distanceah,qtdCovidRealth = load_data(initialTime,durationTime)

testing(CONCapacityrht,InitPatientsph,releasePatientspht,initialTime)

totalVars = len(patTypeList) * len(areaIdList) * len(hosIdList) * len(tList)
print(totalVars)

model = pyo.ConcreteModel()
model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

FATOR_ATAQUE = 0.52

# Step 2: Define the decision 
model.x = pyo.Var(patTypeList, areaIdList, hosIdList, tList, domain = pyo.NonNegativeReals) # (6)  #NonNegativeIntegers
model.y = pyo.Var(patTypeList, hosIdList, tList, domain = pyo.NonNegativeReals) #NonNegativeReals

# Step 3: Define Objective
model.Cost = pyo.Objective(
    expr = sum([Distanceah[a,h]*model.x[p,a,h,t] for p in patTypeList for a in areaIdList for h in hosIdList for t in tList]),
    sense = pyo.minimize)

#model.Infection = pyo.Objective(
#model.Cost = pyo.Objective(
#    expr = sum([qtdCovidRealth.get((t,h),0)*model.x[p,a,h,t]*FATOR_ATAQUE for p in patTypeList for a in areaIdList for h in hosIdList for t in tList]),
#    sense = pyo.minimize)

# Step 4: Constraints
model.demand = pyo.ConstraintList() #(2) do artigo, quantidade de solucoes por trecho nao pode ser maior que a demanda.
for p in patTypeList:
    for a in areaIdList:
        for t in tList:
            model.demand.add(sum([model.x[p,a,h,t] for h in hosIdList]) == Demandpat.get((p,a,t),0))

model.noPattNInicial = pyo.ConstraintList() #(3) do artigo, quantidade de pacientes no instante t é igual ao pacientes t-1 + alocao atual.
for h in hosIdList:
    for p in patTypeList: 
        model.noPattNInicial.add(model.y[p,h,initialTime] == InitPatientsph.get((p,h),0) + sum([model.x[p,a,h,initialTime] for a in areaIdList]))

model.noPattN = pyo.ConstraintList() #(4) do artigo, quantidade de pacientes no instante t é igual ao pacientes t-1 + alocao atual.
for h in tqdm(hosIdList):
    for p in patTypeList: 
        for t in tList:
            if t > initialTime:
                if time_delta(t,-LOSp.get((p),0)) >= initialTime:
                    model.noPattN.add(model.y[p,h,t] == model.y[p,h,time_delta(t,-1)] + sum([model.x[p,a,h,t] for a in areaIdList]) - \
                                    sum([model.x[p,a,h,time_delta(t,-LOSp.get((p),0))] for a in areaIdList]) - \
                                    releasePatientspht.get((p,h,t),0))
                else:
                    model.noPattN.add(model.y[p,h,t] == model.y[p,h,time_delta(t,-1)] + sum([model.x[p,a,h,t] for a in areaIdList]) - \
                    0 - \
                    releasePatientspht.get((p,h,t),0))

model.equipLimit = pyo.ConstraintList() #(5) do artigo, quantidade de pacientes nao pode ser maior que a quantidade de equipamentos.
#for r in equipTypeList:
for p in patTypeList: 
    for h in hosIdList:
        for t in tList:
            model.equipLimit.add(model.y[p,h,t] <= CONCapacityrht.get((p,h,t),0))

print('começou solução modelo: ',datetime.now().strftime("%H:%M:%S"))

#results = pyo.SolverFactory('cbc').solve(model)
results = pyo.SolverFactory('glpk').solve(model)
#results = pyo.SolverFactory('ipopt',executable='./commercial_solvers_bin/ipopt').solve(model)
#results = pyo.SolverFactory('bonmin',executable='./commercial_solvers_bin/bonmin').solve(model)
#results = pyo.SolverFactory('couenne',executable='./commercial_solvers_bin/bonmin').solve(model)
#results = pyo.SolverFactory('gecode',executable='./commercial_solvers_bin/gecode').solve(model)

results.write()

debugList = []
graphList = []

if 'ok' == str(results.Solver.status):
    print("Total Costs = ",model.Cost())
    print("\nShipping Table:")

    for t in tList:
        for p in patTypeList:
            for h in hosIdList:
                for a in areaIdList:
                    if model.x[p,a,h,t]() > 0:
                        debugList.append([p,a,h,t,model.x[p,a,h,t](),model.y[p,h,t](),Distanceah.get((a,h),0)*model.x[p,a,h,t](),qtdCovidRealth.get((t,h),0)*model.x[p,a,h,t]()*FATOR_ATAQUE,CONCapacityrht.get((p,h,t),0),Demandpat.get((p,a,t),0),model.y[p,h,t](),InitPatientsph.get((p,h),0),releasePatientspht.get((p,h,t),0),-LOSp.get((p),0)])
                        graphList.append([t,a,h,model.x[p,a,h,t]()])
                        print(f"At day {t} patient type {p} to hospital {h} from area {a} : {model.x[p,a,h,t]()} | NoPatients pht: {model.y[p,h,t]()} | distancia * alocação: {round(Distanceah.get((a,h),0)*model.x[p,a,h,t](),2)} | custo Infecção : {round(qtdCovidRealth.get((t,h),0)*model.x[p,a,h,t]()*FATOR_ATAQUE,2)} |capacity: {CONCapacityrht.get((p,h,t),0)} | demanda: {Demandpat.get((p,a,t),0)}")

    df = pd.DataFrame(debugList,columns=['p','a','h','t','x','y','custoDistancia','custoInfeccao','capacidadePH','demandaPAT','noPatPHT','initPatPH','releasedPHT','losP']) 
    df.to_csv('debug.csv',index=False)
    graph = pd.DataFrame(graphList,columns=['Timestamps','Source','Target','Weight'])
    graph.to_csv('./data/edgeGraphSimullated.csv',index=False)
else:
    print("No Valid Solution Found")