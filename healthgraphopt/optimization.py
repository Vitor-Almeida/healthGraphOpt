import pyomo.environ as pyo
from utils.utils import time_delta, export_opt_data
from tqdm.auto import tqdm
from datetime import datetime
from utils.unitTest import testing

def run_simulation(initialTime,dataDic):

    patTypeList = dataDic['patTypeList']
    areaIdList = dataDic['areaIdList']
    hosIdList = dataDic['hosIdList']
    equipTypeList = dataDic['equipTypeList']
    tList = dataDic['tList']
    Demandpat = dataDic['DemandCancerpat']
    CONCapacityrht = dataDic['CONCapacityrhCancer']
    InitPatientsph = dataDic['InitPatientsph']
    releasePatientspht = dataDic['releasePatientspht']
    LOSp = dataDic['LOSp']
    Distanceah = dataDic['Distanceah']
    qtdCovidRealth = dataDic['qtdCovidReal']
    qtdProf = dataDic['qtdProf']
    qtdPuraCovidReal = dataDic['qtdPuraCovidReal']
    qtdTT = dataDic['qtdTT']

    testing(CONCapacityrht,InitPatientsph,releasePatientspht,initialTime)

    totalVars = len(patTypeList) * len(areaIdList) * len(hosIdList) * len(tList)
    print(totalVars)

    model = pyo.ConcreteModel()
    model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    FATOR_ATAQUE = 0.52

    # Step 2: Define the decision 
    model.x = pyo.Var(patTypeList, areaIdList, hosIdList, tList, domain = pyo.NonNegativeReals) # (6)  #NonNegativeIntegers
    model.y = pyo.Var(patTypeList, hosIdList, tList, domain = pyo.NonNegativeReals) #NonNegativeReals

    distanceExpr = sum([Distanceah[a,h]*model.x[p,a,h,t] for p in patTypeList for a in areaIdList for h in hosIdList for t in tList])
    infectionExpr = sum([qtdCovidRealth.get((t,h),0)*model.x[p,a,h,t]*FATOR_ATAQUE for p in patTypeList for a in areaIdList for h in hosIdList for t in tList])

    # Step 3: Define Objective
    model.Cost = pyo.Objective(
        expr = distanceExpr,
        sense = pyo.minimize)

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
    for p in patTypeList: 
        for h in hosIdList:
            for t in tList:
                model.equipLimit.add(model.y[p,h,t] <= CONCapacityrht.get((p,h,t),0))

    print('Getting best and worst point of separated solution: ',datetime.now().strftime("%H:%M:%S"))
    results = pyo.SolverFactory('glpk').solve(model)
    bestSolDist = model.Cost()
    model.Cost.sense = pyo.maximize
    results = pyo.SolverFactory('glpk').solve(model)
    worstSolDist = model.Cost()
    model.Cost.expr = infectionExpr
    results = pyo.SolverFactory('glpk').solve(model)
    worstSolInfect = model.Cost()
    model.Cost.sense = pyo.minimize
    results = pyo.SolverFactory('glpk').solve(model)
    bestSolInfect = model.Cost()

    print('Starting weighted-sum method: ',datetime.now().strftime("%H:%M:%S"))
    distanceExpr = (distanceExpr - bestSolDist) / (worstSolDist - bestSolDist)
    infectionExpr = (infectionExpr - bestSolInfect) / (worstSolInfect - bestSolInfect)

    distW = [1.0,0.9,0.8,0.7,0.6,0.5,0.4,0.3,0.2,0.1,0.0]

    for idx,w in enumerate(distW):
        print(f'loop : {idx}')
        model.Cost.expr = round(distW[idx],1)*distanceExpr + round((1-distW[idx]),1)*infectionExpr
        results = pyo.SolverFactory('glpk').solve(model)
        results.write()
        export_opt_data(results,model,tList,patTypeList,hosIdList,areaIdList,qtdPuraCovidReal,
                        qtdProf,Distanceah,qtdCovidRealth,FATOR_ATAQUE,CONCapacityrht,Demandpat,
                        InitPatientsph,releasePatientspht,LOSp,round(distW[idx],1),round(1-distW[idx],1),qtdTT)


#results = pyo.SolverFactory('cbc').solve(model)
#results = pyo.SolverFactory('ipopt',executable='./commercial_solvers_bin/ipopt').solve(model)
#results = pyo.SolverFactory('bonmin',executable='./commercial_solvers_bin/bonmin').solve(model)
#results = pyo.SolverFactory('couenne',executable='./commercial_solvers_bin/bonmin').solve(model)
#results = pyo.SolverFactory('gecode',executable='./commercial_solvers_bin/gecode').solve(model)