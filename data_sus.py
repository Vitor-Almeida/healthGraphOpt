import pandas as pd
import os
import numpy as np
from utils import distance_latLong

class graph_data():

    def __init__(self,initialTime):

        curDir = os.path.dirname(os.path.realpath(__file__))

        fPatPath = os.path.join(curDir,'data','raw','SIH_CE.csv')
        dHosPath = os.path.join(curDir,'data','raw','ST_CNES_CE.csv')
        dEquipPath = os.path.join(curDir,'data','raw','EQ_CNES_CE.csv')
        dLeiPath = os.path.join(curDir,'data','raw','LT_CNES_CE.csv')
        dfLatLongPath = os.path.join(curDir,'data','external','latlongMun.csv')

        self.dffPaciente = pd.read_csv(fPatPath,
                                        sep=",",
                                        encoding='latin',
                                        usecols=['N_AIH','UF_ZI','ESPEC','ANO_CMPT','MES_CMPT','MUNIC_RES',
                                                'NASC','SEXO','DT_INTER','DT_SAIDA','DIAS_PERM','DIAG_PRINC','DIAG_SECUN',
                                                'CNES','MUNIC_MOV','IDADE','MORTE','UTI_MES_TO','MARCA_UTI',
                                                'PROC_SOLIC','PROC_REA','HOMONIMO','CID_ASSO','CID_MORTE',
                                                'COMPLEX','MARCA_UCI','DIAGSEC1','TPDISEC1','DIAGSEC2','TPDISEC2']
                                                )

        self.dfdHosPath = pd.read_csv(dHosPath,
                                        sep=",",
                                        encoding='latin',
                                        usecols=['CNES','CODUFMUN','VINC_SUS','TURNO_AT','TP_UNID','DT_EXPED',
                                                'QTLEITP1','QTLEITP2','QTLEITP3','LEITHOSP','ATENDAMB','CENTROBS',
                                                'CENTRCIR','URGEMERG','CENTRNEO','ATENDHOS','DT_ATUAL','COMPETEN']
                                                )

        self.dfdEquipPath = pd.read_csv(dEquipPath, #nao tem o nome dos equipamento, tem que pesquisa
                                        sep=",",
                                        encoding='latin',
                                        usecols=['CNES','TIPEQUIP','CODEQUIP','QT_EXIST','QT_USO','IND_SUS','IND_NSUS',
                                                    'COMPETEN','TERCEIRO']
                                                )

        self.dfdLeiPath = pd.read_csv(dLeiPath,
                                        sep=",",
                                        encoding='latin',
                                        usecols=['CNES','TP_LEITO','CODLEITO','QT_EXIST','QT_CONTR','QT_SUS','COMPETEN']
                                                )

        self.dfLatLong = pd.read_csv(dfLatLongPath,
                                     sep=",",
                                     encoding="latin")

        self.initialTime = initialTime

        odDf = self._create_od_matrix()
        patDf = self._process_patDf()
        equipDf = self._process_equipDf()
        hospDf = self._process_hosDf()

        #adicionar hospital fantasma


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

    def _create_od_matrix(self):

        arrOrigem = self.dffPaciente[['MUNIC_RES']].drop_duplicates()
        arrDestino = self.dffPaciente[['MUNIC_MOV']].drop_duplicates()

        latLong = self.dfLatLong[['codigo_ibge','latitude','longitude']]

        latLong['codigo_ibge'] = latLong['codigo_ibge'].apply(lambda row: int(str(row)[:-1]))

        arrOrigem = arrOrigem.merge(latLong,left_on='MUNIC_RES',right_on='codigo_ibge')
        arrOrigem.drop(columns=['codigo_ibge'],inplace=True)
        arrDestino = arrDestino.merge(latLong,left_on='MUNIC_MOV',right_on='codigo_ibge')
        arrDestino.drop(columns=['codigo_ibge'],inplace=True)

        arrOrigem['key'] = 0 #cross join gamb
        arrDestino['key'] = 0 #cross join gamb
        arrOrigem = arrOrigem.merge(arrDestino, on='key',how='outer',suffixes=('_ori', '_dest'))

        arrOrigem['DIST'] = arrOrigem.apply(lambda row: distance_latLong(row['latitude_ori'],row['longitude_ori'],row['latitude_dest'],row['longitude_dest']),axis=1)

        ### arrumar, colocar hospital ID: 
        arrOrigem = arrOrigem[['MUNIC_RES','MUNIC_MOV','DIST']]

        return arrOrigem

    def _process_hosDf(self):

        #hosDf =  self.dffPaciente[['CNES','TP_LEITO','QT_SUS','COMPETEN']].drop_duplicates()

        patDfPos = self.dffPaciente.groupby(by=['DIAG_PRINC','DT_INTER','CNES']).agg({'N_AIH':'count'}).reset_index()
        patDfNeg = self.dffPaciente.groupby(by=['DIAG_PRINC','DT_SAIDA','CNES']).agg({'N_AIH':'count'}).reset_index()


        dfResample = pd.concat([self.dffPaciente[['DIAG_PRINC','DT_INTER','CNES']].rename(columns={'DT_INTER':'DT_SAIDA'}),
                                 self.dffPaciente[['DIAG_PRINC','DT_SAIDA','CNES']]
                                ]).drop_duplicates()

        patDfPos.rename(columns={'N_AIH':'QTD_POS'},inplace=True)
        patDfNeg.rename(columns={'N_AIH':'QTD_NEG'},inplace=True)

        dfResample = dfResample.merge(patDfPos,how='left',left_on=['DT_SAIDA','DIAG_PRINC','CNES'],right_on=['DT_INTER','DIAG_PRINC','CNES'])
        dfResample = dfResample.merge(patDfNeg,how='left',left_on=['DT_SAIDA','DIAG_PRINC','CNES'],right_on=['DT_SAIDA','DIAG_PRINC','CNES'])

        dfResample = dfResample[(dfResample['QTD_POS'].notnull()) | (dfResample['QTD_NEG'].notnull())]
        dfResample['QTD_POS'] = dfResample['QTD_POS'].fillna(0)
        dfResample['QTD_NEG'] = dfResample['QTD_NEG'].fillna(0)

        dfResample = dfResample[['DT_SAIDA','CNES','DIAG_PRINC','QTD_POS','QTD_NEG']]
        dfResample.rename(columns={'DT_SAIDA':'DATA'},inplace=True)
        dfResample['QTD_NET'] = dfResample['QTD_POS'] - dfResample['QTD_NEG']
        dfResample.sort_values(by=['DATA','CNES','DIAG_PRINC'],inplace=True)
        dfResample['QTD_ACU'] = dfResample.groupby(['CNES','DIAG_PRINC'])['QTD_NET'].cumsum()

    
        dfResample = dfResample[dfResample['DATA']>=self.initialTime]

        return dfResample

    def _process_equipDf(self):

        dfEquip =  self.dfdLeiPath[['CNES','TP_LEITO','QT_SUS','COMPETEN']].drop_duplicates()
        dfEquip['datetime'] = pd.to_datetime(dfEquip['COMPETEN'], format='%Y%m')
        dfEquip.drop(columns=['COMPETEN'],inplace=True)

        dfEquip.groupby(by=['datetime','TP_LEITO','CNES']).agg({'QT_SUS':'sum'}).reset_index()

        dfResample = pd.date_range(start=min(dfEquip['datetime']),end=max(dfEquip['datetime']),freq='D')
        dfResample = pd.DataFrame(dfResample.values.reshape(len(dfResample),1),columns=['exp_date'])
        dfResample['datetime'] = dfResample['exp_date'].dt.year.astype(str) + "-" + dfResample['exp_date'].dt.month.astype(str) + '-01'
        dfResample['datetime'] = pd.to_datetime(dfResample['datetime'])
        
        dfEquip = dfEquip.merge(dfResample,on='datetime')
        dfEquip.drop(columns=['datetime'],inplace=True)
        dfEquip.rename(columns={'exp_date':'DATA'},inplace=True)

        dfEquip = dfEquip.groupby(by=['CNES','TP_LEITO']).agg({'QT_SUS':'max'}).reset_index()

        dfEquip = dfEquip[dfEquip['QT_SUS']>0] #duvida sobre a permutação ... o dic.get() é para resolver

        return dfEquip

    def _process_patDf(self):

        df = self.dffPaciente[['DT_INTER','MUNIC_RES','DIAG_PRINC']]

        dfMediaStay = self.dffPaciente.groupby(by=['DIAG_PRINC']).agg({'DIAS_PERM':'mean'}).reset_index()
        dfMediaStay['DIAS_PERM'] = round(dfMediaStay['DIAS_PERM'],0).astype(int)

        df = self.dffPaciente.groupby(by=['DT_INTER','MUNIC_RES','DIAG_PRINC']).agg({'N_AIH':'count'}).reset_index()
        
        df = df.merge(dfMediaStay,on=['DIAG_PRINC'])
        df.rename(columns={'N_AIH':'QTY','DIAS_PERM':'MED_PERM'},inplace=True)

        df = df[df['DT_INTER']>=self.initialTime]

        return df


x = graph_data(initialTime=20210101)