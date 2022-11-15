from healthgraphopt.optimization import run_simulation
from dataloader.load_data import load_data
from tqdm.auto import tqdm

def zerar_dic(dataDic,name):

    for n in dataDic[name]:
        dataDic[name][n] = 0

    return dataDic

#def subtrair_dic

def getsom(dataDic,name):

    tmpSom = 0

    for n in dataDic[name]:
        tmpSom = tmpSom + dataDic[name][n]

    return tmpSom

def aumentar_cap(dataDic,name):

    for n in dataDic[name]:
        dataDic[name][n] = 444444

    #dataDic[name][1,2651394,20210407] = 6

    return dataDic

def split(a, n):
    k, m = divmod(len(a), n)
    return (a[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))

def splitDicByDate(dataDic,allTime):

    dataToFilter = ['DemandCancerpat','CONCapacityrhCancer','releasePatientspht','qtdCovidReal','qtdProf','qtdPuraCovidReal','qtdTT']
    dimDic = ['patTypeList','areaIdList','hosIdList','equipTypeList','LOSp','Distanceah','InitPatientsph']

    posTimeCol = [2,2,2,0,1,0,0]
    newDicArray = []
    newDic = {}
    outnewDicArray = []

    for n in allTime:
        n.sort()

    dataListDic = []

    for splits in allTime:
        for n,keyName in enumerate(dataToFilter):
            newDicArray.append( dict(filter(lambda elem: elem[0][posTimeCol[n]] in splits, dataDic[keyName].items())) )

        for n,data in enumerate(newDicArray):
            newDic[dataToFilter[n]] = data

        tList = list(set(dataDic['tList']) & set(splits))
        tList.sort()
        newDic['tList'] = tList.copy()

        for data in dimDic:
            newDic[data] = dataDic[data]

        outnewDicArray.append( newDic.copy() )
        newDicArray = []

    return outnewDicArray

def main():

    initialTime = 20210401
    durationTime = 120
    splitDiv = 14

    dataDic = load_data(initialTime,durationTime)

    ############# QUICK FIXXXX ######################
    #dataDic = zerar_dic(dataDic,'releasePatientspht')
    #dataDic = aumentar_cap(dataDic,'CONCapacityrhCancer')
    #print(getsom(dataDic,'InitPatientsph'))
    ##################################################

    dataDic['tList'].sort()
    allTime = list(split(dataDic['tList'],splitDiv))
    newAllTime = []
    

    #for idx,n in enumerate(allTime):
    #    if idx != 0:
    #        prev = allTime[idx-1][-1]
    #        newAllTime.append([prev]+n)
    #    else:
    #        newAllTime.append(n)
    #allTime = newAllTime.copy()

    weights = [1.0,0.9,0.8,0.7,0.6,0.5,0.4,0.3,0.2,0.1,0.0]

    initPat = dataDic['InitPatientsph'].copy()

    dataDicList = splitDicByDate(dataDic,allTime)

    for weight in tqdm(weights):
        for nToSplit,dDic in enumerate(dataDicList):
            if nToSplit == 0 :
                dDic['InitPatientsph'] = initPat.copy()
                normList = []
                outPutHistConcat = {}
                outPut,outPutHist,normList = run_simulation(allTime[nToSplit][0],dDic,weight,nToSplit,outPutHistConcat,normList)
                outPutHistConcat = outPutHist.copy()
            else:
                #dDic = zerar_dic(dDic,'InitPatientsph')
                #dDic['xContinuidade'] = outPut.copy()
                dDic['InitPatientsph'] = outPut.copy()
                #dDic['InitPatientsph'] = outPut.copy()
                outPut,outPutHist,normList = run_simulation(allTime[nToSplit][0],dDic,weight,nToSplit,outPutHistConcat,normList)

                for key in outPutHist:
                    outPutHistConcat[key] = outPutHist[key]

if __name__ == '__main__':
    main()