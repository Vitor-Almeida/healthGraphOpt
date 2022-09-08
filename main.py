import pyomo.environ as pyo
from utils import time_delta
from load_data import load_data

initialTime=20210101
durationTime=7

patTypeList,areaIdList,hosIdList,equipTypeList,tList,Demandpat,CONCapacityrh,InitPatientsph,releasePatientspht,LOSp,Distanceah = load_data(initialTime,durationTime)

model = pyo.ConcreteModel()
model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

# Step 2: Define the decision 
model.x = pyo.Var(patTypeList, areaIdList, hosIdList, tList, domain = pyo.PositiveReals) # (6)
model.y = pyo.Var(patTypeList, hosIdList, tList, domain = pyo.PositiveReals)

# Step 3: Define Objective
model.Cost = pyo.Objective(
    expr = sum([Distanceah[a,h]*model.x[p,a,h,t] for p in patTypeList for a in areaIdList for h in hosIdList for t in tList]),
    sense = pyo.minimize)

# Step 4: Constraints
model.demand = pyo.ConstraintList() #(2) do artigo, quantidade de solucoes por trecho nao pode ser maior que a demanda.
for p in patTypeList:
    for a in areaIdList:
        for t in tList:
            model.demand.add(sum([model.x[p,a,h,t] for h in hosIdList]) == Demandpat.get((p,a,t),0))

def noPatN(p,h,t):

    if t == initialTime:
        return InitPatientsph.get((p,h),0) + sum([model.x[p,a,h,initialTime] for a in areaIdList])

    elif time_delta(t,-LOSp.get((p),0)) >= initialTime:
        return noPatN(p,h,time_delta(t,-1)) + sum([model.x[p,a,h,t] for a in areaIdList]) - \
               sum([model.x[p,a,h,time_delta(t,-LOSp.get((p),0))]  for a in areaIdList]) - \
               releasePatientspht.get((p,h,t),0)
    else:
        return noPatN(p,h,time_delta(t,-1)) + sum([model.x[p,a,h,t] for a in areaIdList]) - \
               0 - \
               releasePatientspht.get((p,h,t),0)
               #no lugar de -model.x[p,a,h,t-los], usa a base real, um valor escalar e nao variavel.

model.noPattN = pyo.ConstraintList() #(3,4) do artigo, quantidade de pacientes no instante t é igual ao pacientes t-1 + alocao atual.
for p in patTypeList:
    for h in hosIdList:
        for t in tList:
            model.noPattN.add(model.y[p,h,t] == noPatN(p,h,t))

model.equipLimit = pyo.ConstraintList() #(5) do artigo, quantidade de pacientes nao pode ser maior que a quantidade de equipamentos.
for r in equipTypeList:
    for h in hosIdList:
            model.equipLimit.add(sum([model.y[r,h,t] for t in tList]) <= CONCapacityrh.get((r,h),0))

#precisa? x ja foi definido como real nao negativo la em cima.
model.positivo = pyo.ConstraintList() #(6) do artigo, alocação precisa ser positiva
model.positivo.add(sum([model.x[p,a,h,t] for p in patTypeList for a in areaIdList for h in hosIdList for t in tList]) >= 0)

results = pyo.SolverFactory('cbc').solve(model)
#results = pyo.SolverFactory('ipopt',executable='/home/jaco/Projetos/healthGraphOpt/commercial_solvers_bin/ipopt').solve(model)
#results = pyo.SolverFactory('bonmin',executable='/home/jaco/Projetos/healthGraphOpt/commercial_solvers_bin/bonmin').solve(model)
#results = pyo.SolverFactory('couenne',executable='/home/jaco/Projetos/healthGraphOpt/commercial_solvers_bin/bonmin').solve(model)
#results = pyo.SolverFactory('gecode',executable='/home/jaco/Projetos/healthGraphOpt/commercial_solvers_bin/gecode').solve(model)

results.write()

if 'ok' == str(results.Solver.status):
    print("Total Shipping Costs = ",model.Cost())
    print("\nShipping Table:")

    for t in tList:
        for p in patTypeList:
            for h in hosIdList:
                for a in areaIdList:
                    if model.x[p,a,h,t]() > 0:
                        print(f"At day {t} patient type {p} to hospital {h} from area {a} : {model.x[p,a,h,t]()} | NoPatients pht: {model.y[p,h,t]()} | Debug: {noPatN(p,h,t)()}| custo: {round(Distanceah.get((a,h),0)*model.x[p,a,h,t](),2)} | capacity: {CONCapacityrh.get((p,h),0)} | demanda: {Demandpat.get((p,a,t),0)}")
else:
    print("No Valid Solution Found")