import pyomo.environ as pyo
from utils.utils import time_delta, export_opt_data
from datetime import datetime
import pandas as pd
from utils.unitTest import testing
import sys

def export_diccsv(df,name):

    if name == 'Demandpat':
        dfTmp = pd.DataFrame.from_dict(df,orient='index').reset_index()
        dfTmp[['p','a','t']] = pd.DataFrame(dfTmp['index'].tolist(),index=dfTmp.index)
        dfTmp.drop(columns=['index'],inplace=True)
        dfTmp.to_csv(f'{name}.csv',index=False)
    if (name == 'CONCapacityrht' or name == 'releasePatientspht') and df != {}:
        dfTmp = pd.DataFrame.from_dict(df,orient='index').reset_index()
        dfTmp[['p','h','t']] = pd.DataFrame(dfTmp['index'].tolist(),index=dfTmp.index)
        dfTmp.drop(columns=['index'],inplace=True)
        dfTmp.to_csv(f'{name}.csv',index=False)
    if name == 'InitPatientsph':
        dfTmp = pd.DataFrame.from_dict(df,orient='index').reset_index()
        dfTmp[['p','h']] = pd.DataFrame(dfTmp['index'].tolist(),index=dfTmp.index)
        dfTmp.drop(columns=['index'],inplace=True)
        dfTmp.to_csv(f'{name}.csv',index=False)
    if name == 'xContinuidade':
        dfTmp = pd.DataFrame.from_dict(df,orient='index').reset_index()
        dfTmp[['p','h','t']] = pd.DataFrame(dfTmp['index'].tolist(),index=dfTmp.index)
        dfTmp.drop(columns=['index'],inplace=True)
        dfTmp.to_csv(f'{name}.csv',index=False)
    if name == 'outPutHist' and df != {}:
        dfTmp = pd.DataFrame.from_dict(df,orient='index').reset_index()
        dfTmp[['p','a','h','t']] = pd.DataFrame(dfTmp['index'].tolist(),index=dfTmp.index)
        dfTmp.drop(columns=['index'],inplace=True)
        dfTmp.to_csv(f'{name}.csv',index=False)
    if name == 'qtdProf' and df != {}:
        dfTmp = pd.DataFrame.from_dict(df,orient='index').reset_index()
        dfTmp[['h','t']] = pd.DataFrame(dfTmp['index'].tolist(),index=dfTmp.index)
        dfTmp.drop(columns=['index'],inplace=True)
        dfTmp.to_csv(f'{name}.csv',index=False)


    return None

def run_simulation(initialTime,dataDic,weight,split,outPutHistConcat,normList):

    InitPatientsph = dataDic['InitPatientsph']

    tList = dataDic['tList']
    Demandpat = dataDic['DemandCancerpat']
    CONCapacityrht = dataDic['CONCapacityrhCancer']
    releasePatientspht = dataDic['releasePatientspht']
    qtdCovidRealth = dataDic['qtdCovidReal']
    qtdProf = dataDic['qtdProf']
    qtdPuraCovidReal = dataDic['qtdPuraCovidReal']
    qtdTT = dataDic['qtdTT']

    hrsDiaPat = {0:1,1:2} #paciente clinico 1h por dia, paciente cirurgico 2h por dia

    patTypeList = dataDic['patTypeList']
    areaIdList = dataDic['areaIdList']
    hosIdList = dataDic['hosIdList']
    equipTypeList = dataDic['equipTypeList']
    LOSp = dataDic['LOSp']
    Distanceah = dataDic['Distanceah']

    xContinuidade = {}

    export_diccsv(qtdProf,'qtdProf')

    #if split > 0:
    #    xContinuidade = dataDic['xContinuidade']
    #    export_diccsv(xContinuidade,'xContinuidade')
    #export_diccsv(releasePatientspht,'releasePatientspht')
    #export_diccsv(outPutHistConcat,'outPutHist')
    #export_diccsv(Demandpat,'Demandpat')
    #export_diccsv(CONCapacityrht,'CONCapacityrht')
    #export_diccsv(InitPatientsph,'InitPatientsph')
    
    #testing(CONCapacityrht,InitPatientsph,releasePatientspht,initialTime,xContinuidade,split)

    #totalVars = len(patTypeList) * len(areaIdList) * len(hosIdList) * len(tList)
    #print(totalVars)

    model = pyo.ConcreteModel()
    model.dual = pyo.Suffix(direction=pyo.Suffix.IMPORT)

    FATOR_ATAQUE = 0.52

    #fix: redução da capacidade por causa do covid, quando existe alocação no t=0
    ##############################################################################################################################################################
    aumentoTotalCap = 0
    aumentoTotalCapHoras = 0
    for p in patTypeList:
        for h in hosIdList:
            for t in tList:

                initPat = InitPatientsph.get((p,h),0) - sum([outPutHistConcat.get((p,a,h,time_delta(t,-LOSp.get((p),0))),0) for a in areaIdList]) \
                                               - releasePatientspht.get((p,h,t),0)
                cap = CONCapacityrht.get((p,h,t),0)

                capHoras = qtdProf.get((h,t),0)

                if initPat > cap:
                    print('Aumento da capacidade: ',initPat - cap)
                    aumentoTotalCap = aumentoTotalCap + (initPat - cap)
                    CONCapacityrht[p,h,t] = initPat

                if initPat * hrsDiaPat[p] > capHoras:
                    print('Aumento da capacidade Horas: ',initPat * hrsDiaPat[p] - cap)
                    qtdProf[h,t] = initPat * hrsDiaPat[p]
                    aumentoTotalCapHoras = aumentoTotalCapHoras + (initPat * hrsDiaPat[p] - capHoras)
    
    print(f'Aumento total da capacidade: ',aumentoTotalCap)
    print(f'Aumento total da capacidade horas: ',aumentoTotalCapHoras)
    #############################################################################################################################################################

    # Step 2: Define the decision 
    model.x = pyo.Var(patTypeList, areaIdList, hosIdList, tList, domain = pyo.NonNegativeIntegers) # (6)  #NonNegativeIntegers
    model.y = pyo.Var(patTypeList, hosIdList, tList, domain = pyo.NonNegativeIntegers) #NonNegativeReals

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
            model.noPattNInicial.add(model.y[p,h,initialTime] == InitPatientsph.get((p,h),0) + sum([model.x[p,a,h,initialTime] for a in areaIdList]) - \
                                     releasePatientspht.get((p,h,initialTime),0) - sum([outPutHistConcat.get((p,a,h,time_delta(initialTime,-LOSp.get((p),0))),0) for a in areaIdList]))

    model.noPattN = pyo.ConstraintList() #(4) do artigo, quantidade de pacientes no instante t é igual ao pacientes t-1 + alocao atual.
    for h in hosIdList:
        for p in patTypeList: 
            for t in tList:
                if t > initialTime:
                    if time_delta(t,-LOSp.get((p),0)) >= initialTime:
                        model.noPattN.add(model.y[p,h,t] == model.y[p,h,time_delta(t,-1)] + sum([model.x[p,a,h,t] for a in areaIdList]) - \
                                        sum([model.x[p,a,h,time_delta(t,-LOSp.get((p),0))] for a in areaIdList]) - \
                                        releasePatientspht.get((p,h,t),0))
                    else:
                        model.noPattN.add(model.y[p,h,t] == model.y[p,h,time_delta(t,-1)] + sum([model.x[p,a,h,t] for a in areaIdList]) - \
                        sum([outPutHistConcat.get((p,a,h,time_delta(t,-LOSp.get((p),0))),0) for a in areaIdList]) - \
                        releasePatientspht.get((p,h,t),0))

    model.equipLimit = pyo.ConstraintList() #(5) do artigo, quantidade de pacientes nao pode ser maior que a quantidade de equipamentos.
    for p in patTypeList: 
        for h in hosIdList:
            for t in tList:
                model.equipLimit.add(model.y[p,h,t] <= CONCapacityrht.get((p,h,t),0))

    model.staffHrs = pyo.ConstraintList() #(5) do artigo, quantidade de pacientes nao pode ser maior que a quantidade de horas dos médicos.
    for p in patTypeList: 
        for h in hosIdList:
            for t in tList:
                model.staffHrs.add(model.y[p,h,t] * hrsDiaPat[p] <= qtdProf.get((h,t),0))

    if split == 0:
        print('Getting best and worst point of separated solution: ',datetime.now().strftime("%H:%M:%S"))
        results = pyo.SolverFactory('glpk').solve(model)#,tee=True)
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
        normList = [bestSolDist,worstSolDist,worstSolInfect,bestSolInfect]
    else:
        bestSolDist = normList[0]
        worstSolDist = normList[1]
        worstSolInfect = normList[2]
        bestSolInfect = normList[3]

    print('Starting weighted-sum method: ',datetime.now().strftime("%H:%M:%S"))
    distanceExpr = (distanceExpr - bestSolDist) / (worstSolDist - bestSolDist)
    infectionExpr = (infectionExpr - bestSolInfect) / (worstSolInfect - bestSolInfect)

    model.Cost.expr = round(weight,1)*distanceExpr + round((1-weight),1)*infectionExpr
    results = pyo.SolverFactory('glpk').solve(model)
    #results.write()
    outPut,outPutHist = export_opt_data(results,model,tList,patTypeList,hosIdList,areaIdList,qtdPuraCovidReal,
                    qtdProf,Distanceah,qtdCovidRealth,FATOR_ATAQUE,CONCapacityrht,Demandpat,
                    InitPatientsph,releasePatientspht,LOSp,round(weight,1),round(1-weight,1),qtdTT,split)
    print('terminou 1')
    return outPut,outPutHist,normList

#results = pyo.SolverFactory('cbc').solve(model)
#results = pyo.SolverFactory('ipopt',executable='./commercial_solvers_bin/ipopt').solve(model)
#results = pyo.SolverFactory('bonmin',executable='./commercial_solvers_bin/bonmin').solve(model)
#results = pyo.SolverFactory('couenne',executable='./commercial_solvers_bin/bonmin').solve(model)
#results = pyo.SolverFactory('gecode',executable='./commercial_solvers_bin/gecode').solve(model)