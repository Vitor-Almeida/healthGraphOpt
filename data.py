import pandas as pd

class graph_data():

    def __init__(self):

        dfdHospital = pd.read_csv('/home/jaco/Projetos/healthGraphOpt/data/dHospital.csv')
        dfmOD = pd.read_csv('/home/jaco/Projetos/healthGraphOpt/data/mOD.csv')
        dffPaciente = pd.read_csv('/home/jaco/Projetos/healthGraphOpt/data/fPaciente.csv')

        dfmOD = dfmOD.melt(id_vars='areaId',var_name='hosId',value_name='dist')
        dfmOD['areaId']=dfmOD['areaId'].astype(int)
        dfmOD['hosId']=dfmOD['hosId'].astype(int)
        dfmOD['dist']=dfmOD['dist'].astype(float)
        dfmOD.set_index(['areaId','hosId'],inplace=True)

        
        dffPaciente['areaId']=dffPaciente['areaId'].astype(int)
        dffPaciente['patTypeId']=dffPaciente['patTypeId'].astype(int)
        dffPaciente['qty']=dffPaciente['qty'].astype(int)

        dffDemanda = dffPaciente.groupby(by=['dia','areaId','areaName','patTypeId','patTypeName']).agg({'qty':'sum'}).reset_index()
        dffDemanda.set_index(['patTypeId','areaId','dia'],inplace=True)
  
        dfCONcapacity = dfdHospital.groupby(by=['hosId','hosName','equipId','equipName']).agg({'initialEquipCap':'sum'}).reset_index()
        dfCONcapacity.set_index(['equipId','hosId'],inplace=True)

        dfInitPatientsph = dfdHospital.groupby(by=['hosId','hosName','initalPatType']).agg({'initialPat':'sum','ReleasePatt':'sum'}).reset_index()
        dfInitPatientsph.set_index(['initalPatType','hosId'],inplace=True)

        dfAvgLenStay = dffPaciente[['patTypeId','AvgLenStay']].drop_duplicates()
        dfAvgLenStay.set_index(['patTypeId'],inplace=True)

        #dfmOD.reset_index(inplace=True)

        self.patTypeList = list(dffPaciente['patTypeId'].drop_duplicates())
        self.areaIdList = list(dffPaciente['areaId'].drop_duplicates())
        self.hosIdList = list(dfdHospital['hosId'].drop_duplicates())
        self.equipIdList = list(dfdHospital['equipId'].drop_duplicates())
        self.tList = list(dffPaciente['dia'].drop_duplicates())

        self.Demandpat = {index:row['qty'] for index, row in dffDemanda.iterrows()}

        self.CONCapacityrh  = {index:row['initialEquipCap'] for index, row in dfCONcapacity.iterrows()} 

        self.InitPatientsph  = {index:row['initialPat'] for index, row in dfInitPatientsph.iterrows()} 

        self.releasePatientsph  = {index:row['ReleasePatt'] for index, row in dfInitPatientsph.iterrows()}

        self.LOSp = {index:row['AvgLenStay'] for index, row in dfAvgLenStay.iterrows()}

        self.Distanceah = {index:row['dist'] for index, row in dfmOD.iterrows()}
