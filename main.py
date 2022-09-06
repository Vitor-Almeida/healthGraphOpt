import pyomo.environ as pyo
from data import graph_data

data = graph_data()
Demandpat = data.Demandpat
CONCapacityrh  = data.CONCapacityrh
InitPatientsph  = data.InitPatientsph
releasePatientsph  = data.releasePatientsph
LOSp = data.LOSp
Distanceah = data.Distanceah

model = pyo.ConcreteModel()
model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

# Step 1: Define index sets
patTypeList = data.patTypeList
equipTypeList = data.equipIdList
areaIdList = data.areaIdList
hosIdList = data.hosIdList
tList = data.tList

# Step 2: Define the decision 
model.x = pyo.Var(patTypeList, areaIdList, hosIdList, tList, domain = pyo.NonNegativeReals) # (6)
model.y = pyo.Var(patTypeList, hosIdList, tList, domain = pyo.NonNegativeReals)

# Step 3: Define Objective
model.Cost = pyo.Objective(
    expr = sum([Distanceah[a,h]*model.x[p,a,h,t] for p in patTypeList for a in areaIdList for h in hosIdList for t in tList]),
    sense = pyo.minimize)

# Step 4: Constraints
model.demand = pyo.ConstraintList() #(2) do artigo, quantidade de solucoes por trecho nao pode ser maior que a demanda.
for p in patTypeList:
    for a in areaIdList:
        for t in tList:
            model.demand.add(sum([model.x[p,a,h,t] for h in hosIdList]) == Demandpat[p,a,t] )

def noPatN(p,h,t):

    if t == 0:
        return InitPatientsph[p,h] + sum([model.x[p,a,h,0] for a in areaIdList])
    else:
        return noPatN(p,h,t-1) + sum([model.x[p,a,h,t] for a in areaIdList]) - \
               sum([model.x[p,a,h,t] - LOSp[p] for a in areaIdList]) - \
               releasePatientsph[p,h] #no artigo é por t (faz sentido?)

model.noPattN = pyo.ConstraintList() #(3,4) do artigo, quantidade de pacientes no instante t é igual ao pacientes t-1 + alocao atual.
for p in patTypeList:
    for h in hosIdList:
        for t in tList:
                model.noPattN.add(model.y[p,h,t] == noPatN(p,h,t))

model.equipLimit = pyo.ConstraintList() #(5) do artigo, quantidade de pacientes nao pode ser maior que a quantidade de equipamentos.

for r in equipTypeList:
    for h in hosIdList:
            model.equipLimit.add(sum([model.y[r,h,t] for t in tList]) <= CONCapacityrh[r,h])


#precisa? x ja foi definido como real nao negativo la em cima.
#model.positivo = ConstraintList() #(6) do artigo, alocação precisa ser positiva
#model.positivo.add(sum([model.x[p,a,h,t] for p in patTypeList for a in areaIdList for h in hosIdList for t in tList]) >= 0)

results = pyo.SolverFactory('cbc').solve(model)
results.write()

if 'ok' == str(results.Solver.status):
    print("Total Shipping Costs = ",model.Cost())
    print("\nShipping Table:")
    for p in patTypeList:
        for a in areaIdList:
            for h in hosIdList:
                for t in tList:
                    if model.x[p,a,h,t]() > 0:
                        print(f"Ship from {a} to {h} patient type {p} at day {t} : {model.x[p,a,h,t]()}")
else:
    print("No Valid Solution Found")