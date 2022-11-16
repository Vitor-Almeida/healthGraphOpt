from math import sin, cos, sqrt, atan2, radians
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def _normalize_demand(dfDemandaCancer:pd.DataFrame, initialTime:int,finialTime:int):

    alldates = pd.date_range(start=datetime.strptime(str(initialTime), '%Y%m%d'),
                                 end=datetime.strptime(str(finialTime), '%Y%m%d'),freq='D')

    timeSeires = [dates.year*10000 + dates.month*100 + dates.day for dates in alldates]

    dfDemandaCancer['WEEKDAY'] = dfDemandaCancer['Timestamp'].apply(datetime.weekday)

    meanDivision = dfDemandaCancer[['DT_INTER','WEEKDAY']].drop_duplicates()
    meanDivision = meanDivision.groupby(by=['WEEKDAY']).agg({'DT_INTER':'count'}).reset_index()
    meanDivision.rename(columns={'DT_INTER':'DIVISOR'},inplace=True)

    dfDemandaCancer = dfDemandaCancer.groupby(by=['MUNIC_RES','TP_PAC_AGRP','WEEKDAY']).agg({'QTY':'sum'}).reset_index()
    dfDemandaCancer = dfDemandaCancer.merge(meanDivision,how='inner',on=['WEEKDAY'])
    
    dfDemandaCancer['QTY'] = dfDemandaCancer['QTY'] / dfDemandaCancer['DIVISOR']
    dfDemandaCancer.drop(columns=['DIVISOR'],inplace=True)

    timeSeires = np.expand_dims(timeSeires,axis=1)
    timeSeiresDf = pd.DataFrame(timeSeires,columns=['DT_INTER'])
    timeSeiresDf['Timestamp'] = pd.to_datetime(timeSeiresDf['DT_INTER'], format='%Y%m%d')
    timeSeiresDf['WEEKDAY'] = timeSeiresDf['Timestamp'].apply(datetime.weekday)

    dfDemandaCancer = timeSeiresDf.merge(dfDemandaCancer,how='inner',on=['WEEKDAY'])

    dfDemandaCancer = dfDemandaCancer[['DT_INTER','MUNIC_RES','TP_PAC_AGRP','QTY']]

    totalToChose = round(dfDemandaCancer[dfDemandaCancer['QTY']<1]['QTY'].sum())

    dfDemandaCancer['UF'] = dfDemandaCancer['MUNIC_RES'].astype(str).str[:2]

    dfDemandaCancer = dfDemandaCancer[dfDemandaCancer['UF']=='23']
    dfDemandaCancer.drop(columns=['UF'],inplace=True)

    arrToChose = dfDemandaCancer[dfDemandaCancer['QTY']<1]
    #totalToChose = round(arrToChose['QTY'].sum())
    escohla = np.random.choice(arrToChose.index.to_numpy(),size=totalToChose,replace=False)

    arrToChose = arrToChose[arrToChose.index.isin(escohla)]
    arrToChose['QTY'] = 1

    dfDemandaCancer = dfDemandaCancer[dfDemandaCancer['QTY']>=1]
    dfDemandaCancer['QTY'] = dfDemandaCancer['QTY'].round(decimals=0)

    dfDemandaCancer = pd.concat([dfDemandaCancer,arrToChose],ignore_index=True)

    dfDemandaCancer['QTY'] = dfDemandaCancer['QTY'].astype(int)

    return dfDemandaCancer


def time_delta(int_time:int,delta:int) -> int:

    '''Only accepts date in format 20211201 as a integer. positive delta indicates
    that is a sum, negative delta indicates that is a subtraction'''

    int_time = datetime.strptime(str(int_time), '%Y%m%d')

    int_time = int_time + timedelta(days = int(delta))

    return int_time.year*10000 + int_time.month*100 + int_time.day*1

def distance_latLong(lat1,lon1,lat2,lon2):

    # approximate radius of earth in km
    R = 6373.0

    lat1 = radians(lat1)
    lon1 = radians(lon1)
    lat2 = radians(lat2)
    lon2 = radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    if R * c == 0:
        distance = 1.0
    else:
        distance = R * c

    return distance


def export_opt_data(results,model,tList,patTypeList,hosIdList,areaIdList,qtdPuraCovidReal,
                    qtdProf,Distanceah,qtdCovidRealth,FATOR_ATAQUE,CONCapacityrht,Demandpat,
                    InitPatientsph,releasePatientspht,LOSp,Wdist,Winf,qtdTT,split):
    debugList = []
    graphList = []
    outPut = {}
    outPutHist = {}

    if 'ok' == str(results.Solver.status):
        #print("Total Costs = ",model.Cost())

        for t in tList:
            for p in patTypeList:
                for h in hosIdList:

                    for a in areaIdList:

                        if model.y[p,h,t]() > 0 and t == tList[-1]:
                            outPut[(p,h)] = int(model.y[p,h,t]())

                        if model.x[p,a,h,t]() > 0:
                            outPutHist[(p,a,h,t)] = int(model.x[p,a,h,t]())

                        if model.x[p,a,h,t]() > 0 or qtdPuraCovidReal.get((t,h),0) > 0 or CONCapacityrht.get((p,h,t),0) > 0: 
                        #if model.x[p,a,h,t]() > 0: 
                            #montar mais .csv

                            debugList.append([Wdist,Winf,p,a,h,t,
                                              model.x[p,a,h,t](),model.y[p,h,t](),qtdPuraCovidReal.get((t,h),0),qtdProf.get((h,t),0),
                                              Distanceah.get((a,h),0)*model.x[p,a,h,t](),qtdCovidRealth.get((t,h),0)*model.x[p,a,h,t]()*FATOR_ATAQUE,CONCapacityrht.get((p,h,t),0),
                                              Demandpat.get((p,a,t),0),model.y[p,h,t](),InitPatientsph.get((p,h),0),releasePatientspht.get((p,h,t),0),-LOSp.get((p),0),
                                              qtdTT.get((t,h),0), model.y[1,h,t]() + model.y[0,h,t]() ])
                            graphList.append([t,a,h,model.x[p,a,h,t]()])

        df = pd.DataFrame(debugList,columns=['Wdist','Winf','p','a','h','t',
                                            'x','y','qtdCovid','qtdProf',
                                            'custoDistancia','custoInfeccao','capacidadePH',
                                            'demandaPAT','noPatPHT','initPatPH','releasedPHT','losP',
                                            'qtyOutrosHT','qtyCancerHT']) 
        df.to_csv(f'./data/processed/integer/debug_D{Wdist}_I{Winf}_S{split}.csv',index=False)
        graph = pd.DataFrame(graphList,columns=['Timestamps','Source','Target','Weight'])
        graph.to_csv(f'./data/processed/edgeGraph/edgeGraphSimullated_D{Wdist}_I{Winf}_S{split}.csv',index=False)
    else:
        print("No Valid Solution Found")


    return outPut, outPutHist