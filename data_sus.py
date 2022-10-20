import pandas as pd
import os
import numpy as np
from utils import distance_latLong, time_delta, _normalize_demand
import itertools
import pickle
from datetime import datetime
from deParas import _load_deparas, encoding_patType, _create_dyn_qtd

def fix_initial_cap(row):

    if row['CNES'] != 0 :
        if row['QT_SUS'] <= row['QTD_ACU'] + row['RELEASE_MAX']: #row['RELEASE_MAX'] nao tava precisando
            row['QT_SUS'] = row['QTD_ACU'] + row['RELEASE_MAX']

    return row

class graph_data():

    def __init__(self,initialTime,durationTime):

        self.curDir = os.path.dirname(os.path.realpath(__file__))
        fPatPath = os.path.join(self.curDir,'data','raw','SIH_CE.csv')
        dHosPath = os.path.join(self.curDir,'data','raw','ST_CNES_CE.csv')
        dEquipPath = os.path.join(self.curDir,'data','raw','EQ_CNES_CE.csv')
        dProfPath = os.path.join(self.curDir,'data','raw','PF_CNES_CE.csv')
        dLeiPath = os.path.join(self.curDir,'data','raw','LT_CNES_CE.csv')
        dfLatLongPath = os.path.join(self.curDir,'data','external','latlongMun.csv')
        self.initialTime = initialTime
        self.durationTime = durationTime
        self.finialTime = time_delta(self.initialTime,+self.durationTime)

        self.dffPaciente = pd.read_csv(fPatPath,
                                       sep=",",
                                       encoding='latin',
                                       usecols=['N_AIH','UF_ZI','ESPEC','ANO_CMPT','MES_CMPT','MUNIC_RES','PROC_REA',
                                                'NASC','SEXO','DT_INTER','DT_SAIDA','DIAS_PERM','DIAG_PRINC','DIAG_SECUN',
                                                'CNES','MUNIC_MOV','IDADE','MORTE','UTI_MES_TO','MARCA_UTI',
                                                'PROC_SOLIC','PROC_REA','HOMONIMO','CID_ASSO','CID_MORTE',
                                                'COMPLEX','MARCA_UCI','DIAGSEC1','TPDISEC1','DIAGSEC2','TPDISEC2'])

        self.dffProfission = pd.read_csv(dProfPath,
                                       sep=",",
                                       encoding='latin',
                                       usecols=['CNES','CBO','HORA_AMB','HORAHOSP','HORAOUTR','COMPETEN'])

        self.dfdHosPath = pd.read_csv(dHosPath,
                                      sep=",",
                                      encoding='latin',
                                      usecols=['CNES','CODUFMUN','VINC_SUS','TURNO_AT','TP_UNID','DT_EXPED',
                                               'QTLEITP1','QTLEITP2','QTLEITP3','LEITHOSP','ATENDAMB','CENTROBS',
                                               'CENTRCIR','URGEMERG','CENTRNEO','ATENDHOS','DT_ATUAL','COMPETEN'])

        self.dfdLeiPath = pd.read_csv(dLeiPath,
                                      sep=",",
                                      encoding='latin',
                                      usecols=['CNES','TP_LEITO','CODLEITO','QT_EXIST','QT_CONTR','QT_SUS','COMPETEN'])

        self.dfLatLong = pd.read_csv(dfLatLongPath,
                                     sep=",",
                                     encoding="latin",
                                     usecols=['codigo_ibge','latitude','longitude','capital'])

        self.dffPaciente, self.dfdLeiPath, dfDemandaCancer, self.dffProfission = _load_deparas(self.dffPaciente,self.dfdLeiPath,self.dffProfission)

        dfDemandaCancer = _normalize_demand(dfDemandaCancer,self.initialTime,self.finialTime)

        self._create_bi_data_host_ocu()
        dffProfQty, dffProfHrs = self._create_prof_data()
        odDf = self._create_od_matrix() #sai do real também, nao era pra sair do real, talvez rodar ela antes do filtro da data.
        self._create_real_patdf() #exportar csvs para o gephi no windows.
        patDf = self._process_patDf() #junta a média da stay
        equipDf = self._process_equipDf()
        hospDf,_ = self._process_hosDf(colName='TP_PAC_AGRP') #ta saindo da tabela real, teria que puxar da tabela de estabelecimento mesmo. Isso aqui é a tabela de demanda/release, nao é dimhosp, tem q no minimo fazer a permutação total CNES vs DIA
        hospDfAgr,dfAjusteEquip = self._process_hosDf(colName='TP_PAC_AGRP_AGRUPADA')
        hospDfAgr.rename(columns={'TP_PAC_AGRP_AGRUPADA':'TP_PAC_AGRP'},inplace=True)
        dfAjusteEquip.rename(columns={'TP_PAC_AGRP_AGRUPADA':'TP_PAC_AGRP'},inplace=True)

        listaHosp = np.unique(self.dffPaciente['CNES']).tolist() + [0]

        patDf = patDf[(patDf['DT_INTER']>=self.initialTime) & (patDf['DT_INTER']<self.finialTime)]

        hospDfCovid = hospDf.copy(deep=True)
        hospDfCovid = hospDfCovid[(hospDfCovid['TP_PAC_AGRP']=='COVID_CLINICOS') | (hospDfCovid['TP_PAC_AGRP']=='COVID_CIRURGIA')]
        hospDfCovid.drop(columns=['TP_PAC_AGRP'],inplace=True)
        hospDfCovid = hospDfCovid.groupby(by=['DATA','CNES']).agg({'QTD_POS':'sum','QTD_NEG':'sum','QTD_NET':'sum','QTD_ACU':'sum','QTD_RELEASE':'sum'}).reset_index()
        hospDfCovid = hospDfCovid[['DATA','CNES','QTD_ACU']]
        hospDfCovid = hospDfCovid.astype(int)

        ghostHospDATA = [hospDfCovid['DATA'].tolist()]
        ghostHospCNES = [0] * len(hospDfCovid)
        ghostHospQTDACU = [999999] * len(hospDfCovid)

        ghostHospDATA.append(ghostHospCNES)
        ghostHospDATA.append(ghostHospQTDACU)
        ghostHosp = np.array(ghostHospDATA).T
        ghostHosp = pd.DataFrame(ghostHosp,columns=['DATA','CNES','QTD_ACU'])
        ghostHosp['CNES'] = ghostHosp['CNES'].astype(int)
        ghostHosp['DATA'] = ghostHosp['DATA'].astype(int)
        ghostHosp['QTD_ACU'] = ghostHosp['QTD_ACU'].astype(int)
        ghostHosp = ghostHosp.drop_duplicates()

        hospDfCovid = pd.concat([hospDfCovid,ghostHosp],ignore_index=True)

        ######## NAN ################
        hospDfAgr = hospDfAgr.merge(equipDf, how='left', left_on=['TP_PAC_AGRP','CNES','DATA'], right_on=['DESC_LEITO','CNES','DATA']) #olhar os NAN!
        ajustEquip = hospDfAgr[hospDfAgr['QT_SUS'].isnull()]
        ajustEquip = ajustEquip.merge(dfAjusteEquip,how='inner',on=['TP_PAC_AGRP','CNES'])
        ajustEquip.drop(columns=['QT_SUS','DESC_LEITO'],inplace=True)
        ajustEquip.rename(columns={'QTD_SUS_AJ':'QT_SUS'},inplace=True)

        hospDfAgr.drop(columns=['DESC_LEITO'],inplace=True)
        hospDfAgr = hospDfAgr[hospDfAgr['QT_SUS']>0] #aqui ta tirando os NAN
        hospDfAgr = pd.concat([hospDfAgr,ajustEquip],ignore_index=False) #ajustando leitos n-existentes
        hospDfAgr = hospDfAgr.sort_values(by=['DATA','CNES','TP_PAC_AGRP'])
        hospDfAgr = self._create_ghost_hosp(hospDfAgr)
        ##############################

        ##encoding do tipo de paciente:
        patDf,hospDfAgr,dfDemandaCancer,encdF = encoding_patType(patDf,hospDfAgr,dfDemandaCancer)

        #### correções de dados gov #####################################

        relSum = hospDfAgr.groupby(by=['CNES','TP_PAC_AGRP']).agg({'QTD_RELEASE':'sum'}).reset_index()
        relSum.rename(columns={'QTD_RELEASE':'RELEASE_MAX'},inplace=True)
        hospDfAgr = hospDfAgr.merge(relSum,how='left',left_on=['CNES','TP_PAC_AGRP'],right_on=['CNES','TP_PAC_AGRP'])

        hospDfAgr = hospDfAgr.apply(fix_initial_cap,axis=1) #ajustando para capacidade inicial >= pat inicial + release do periodo
        hospDfAgr.drop(columns=['RELEASE_MAX'],inplace=True)

        #hospSIMPLIFICADO['QTD_ACU'] = hospSIMPLIFICADO['QTD_ACU'] + 500  # nao pode ter releasett > qtd inicial para nenhuma combinação !!!
        #hospSIMPLIFICADO['QT_SUS'] = 99999 # tem que garantir aqui q tenha capacidade inicial >= demanda inicial

        ##################################################################

        ### criar hospDf com equip sendo alterado ###############:

        CancerhospDf = _create_dyn_qtd(hospDfAgr,encdF)

        odDf=odDf[odDf['MUNIC_RES'].isin(dfDemandaCancer['MUNIC_RES'].drop_duplicates())]
        odDf=odDf[odDf['CNES'].isin(listaHosp)]

        hospDfCovid = hospDfCovid.astype(int)

        hospDfCovid = hospDfCovid.merge(dffProfQty, how = 'inner', on=['DATA','CNES'])
        hospDfCovid['QTY_TT'] = hospDfCovid['QTY'] * hospDfCovid['QTD_ACU']
        hospDfCovid.drop(columns=['QTY','QTD_ACU'],inplace=True)
        hospDfCovid.rename(columns={'QTY_TT':'QTY'},inplace=True)
        hospDfCovid = hospDfCovid[hospDfCovid['QTY']>0]

        #hospDfCovid = self._create_ghost_hosp(hospDfAgr)

        hospDfCovid.set_index(['DATA','CNES'],inplace=True)

        ##########################################################

        odDf.set_index(['MUNIC_RES','CNES'],inplace=True)

        dfDCancer = dfDemandaCancer.set_index(['TP_PAC_AGRP','MUNIC_RES','DT_INTER'])
  
        dfCONcapacityCancer = CancerhospDf[['DATA','TP_PAC_AGRP','CNES','QT_SUS']].set_index(['TP_PAC_AGRP','CNES','DATA'])

        dfInitPatientsphCancer = CancerhospDf[['CNES','TP_PAC_AGRP','QTD_ACU']][CancerhospDf['DATA']==min(CancerhospDf['DATA'])].drop_duplicates()
        dfInitPatientsphCancer = dfInitPatientsphCancer[dfInitPatientsphCancer['QTD_ACU']>0]
        dfInitPatientsphCancer.set_index(['TP_PAC_AGRP','CNES'],inplace=True)

        dfReleasePattCancer = CancerhospDf[['DATA','TP_PAC_AGRP','CNES','QTD_RELEASE']]
        dfReleasePattCancer = dfReleasePattCancer[dfReleasePattCancer['QTD_RELEASE']>0]
        dfReleasePattCancer.set_index(['TP_PAC_AGRP','CNES','DATA'],inplace=True)

        dfAvgLenStay = patDf.merge(encdF[(encdF['TP_PAC_AGRP']=='CANCER_CIRURGIA') | (encdF['TP_PAC_AGRP']=='CANCER_CLINICOS')].reset_index()[['IDX']],how='inner',left_on=['TP_PAC_AGRP'],right_on=['IDX'])
        dfAvgLenStay = dfAvgLenStay[['TP_PAC_AGRP','MED_PERM']].drop_duplicates()
        dfAvgLenStay.set_index(['TP_PAC_AGRP'],inplace=True)

        self.patTypeList = dfDemandaCancer['TP_PAC_AGRP'].drop_duplicates().tolist()
        self.patTypeList.sort()
        self.equipIdList = dfDemandaCancer['TP_PAC_AGRP'].drop_duplicates().tolist()
        self.equipIdList.sort()
        self.areaIdList = dfDemandaCancer['MUNIC_RES'].drop_duplicates().tolist()
        self.hosIdList = listaHosp

        self.tList = [time_delta(self.initialTime,+n) for n in range(self.durationTime)]

        self.qtdCovidReal = {index:row['QTY'] for index, row in hospDfCovid.iterrows()}

        self.DemandCancerpat = {index:row['QTY'] for index, row in dfDCancer.iterrows()}

        self.CONCapacityrhCancer  = {index:row['QT_SUS'] for index, row in dfCONcapacityCancer.iterrows()}

        self.InitPatientsphCancer  = {index:row['QTD_ACU'] for index, row in dfInitPatientsphCancer.iterrows()} 

        self.releasePatientsphtCancer  = {index:row['QTD_RELEASE'] for index, row in dfReleasePattCancer.iterrows()}

        self.LOSp = {index:row['MED_PERM'] for index, row in dfAvgLenStay.iterrows()}

        self.Distanceah = {index:row['DIST'] for index, row in odDf.iterrows()}

        self._save_pickle()

    def _save_pickle(self):

        with open('./data/bin/patTypeList.pkl', 'wb') as f:
            pickle.dump(self.patTypeList, f)
            f.close()
        with open('./data/bin/areaIdList.pkl', 'wb') as f:
            pickle.dump(self.areaIdList, f)
            f.close()
        with open('./data/bin/hosIdList.pkl', 'wb') as f:
            pickle.dump(self.hosIdList, f)
            f.close()
        with open('./data/bin/equipIdList.pkl', 'wb') as f:
            pickle.dump(self.equipIdList, f)
            f.close()
        with open('./data/bin/tList.pkl', 'wb') as f:
            pickle.dump(self.tList, f)
            f.close()
        with open('./data/bin/DemandCancerpat.pkl', 'wb') as f:
            pickle.dump(self.DemandCancerpat, f)
            f.close()
        with open('./data/bin/CONCapacityrhCancer.pkl', 'wb') as f:
            pickle.dump(self.CONCapacityrhCancer, f)
            f.close()
        with open('./data/bin/InitPatientsphCancer.pkl', 'wb') as f:
            pickle.dump(self.InitPatientsphCancer, f)
            f.close()
        with open('./data/bin/releasePatientsphtCancer.pkl', 'wb') as f:
            pickle.dump(self.releasePatientsphtCancer, f)
            f.close()
        with open('./data/bin/LOSp.pkl', 'wb') as f:
            pickle.dump(self.LOSp, f)
            f.close()
        with open('./data/bin/Distanceah.pkl', 'wb') as f:
            pickle.dump(self.Distanceah, f)
            f.close()
        with open('./data/bin/qtdCovidReal.pkl', 'wb') as f:
            pickle.dump(self.qtdCovidReal, f)
            f.close()

        return None

    def _create_ghost_hosp(self,hospDf:pd.DataFrame):

        allDates = hospDf['DATA'].drop_duplicates().tolist()
        allEquip = hospDf['TP_PAC_AGRP'].drop_duplicates().tolist()

        prods = itertools.product(allDates,allEquip)
        ghostDfNP2d = []

        for n in prods:
            ghostDfNP2d.append([n[0],n[1],99999999,0,0,0,0,0,0])

        dfFantasma = pd.DataFrame(ghostDfNP2d,columns=['DATA','TP_PAC_AGRP','QT_SUS','CNES','QTD_POS','QTD_NEG','QTD_NET','QTD_ACU','QTD_RELEASE'])

        dfFantasma = dfFantasma[['DATA','CNES','TP_PAC_AGRP','QTD_POS','QTD_NEG','QTD_NET','QTD_ACU','QTD_RELEASE','QT_SUS']]

        dfFantasma = pd.concat([hospDf,dfFantasma],ignore_index=True)

        dfFantasma[['QTD_POS','QTD_NEG','QTD_NET','QTD_ACU','QTD_RELEASE','QT_SUS']] = dfFantasma[['QTD_POS','QTD_NEG','QTD_NET','QTD_ACU','QTD_RELEASE','QT_SUS']].astype(int)

        ######

        return dfFantasma

    def _create_od_matrix(self):

        arrOrigem = self.dffPaciente[['MUNIC_RES']].drop_duplicates()
        arrDestino = self.dffPaciente[['MUNIC_MOV']].drop_duplicates()

        dfCnesLocal = self.dffPaciente[['CNES','MUNIC_MOV']].drop_duplicates() ###usando a base real pra pegar todos os pares cnes,munic_mov, mais correto é usar a dimhos

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

        arrOrigem = arrOrigem[['MUNIC_RES','MUNIC_MOV','DIST']]
        arrOrigem.to_csv(os.path.join(self.curDir,'data','external','distsBI.csv'),index=False)

        arrOrigem = arrOrigem.merge(dfCnesLocal,how='left',left_on='MUNIC_MOV',right_on='MUNIC_MOV')
        arrOrigem = arrOrigem[['MUNIC_RES','CNES','DIST']]

        ######fantasma:

        allMunicList = [arrOrigem['MUNIC_RES'].drop_duplicates().tolist()]
        ghostHospList = [0] * len(allMunicList[0])
        maxDistList = [99999.9] * len(allMunicList[0])
        allMunicList.append(ghostHospList)
        allMunicList.append(maxDistList)
        ghostDfNP2d = np.array(allMunicList).T

        dfFantasma = pd.DataFrame(ghostDfNP2d,columns=['MUNIC_RES','CNES','DIST'])
        dfFantasma['MUNIC_RES'] = dfFantasma['MUNIC_RES'].astype(int)
        dfFantasma['CNES'] = dfFantasma['CNES'].astype(int)
        dfFantasma['DIST'] = dfFantasma['DIST'].astype(float)

        ######

        arrOrigem = pd.concat([arrOrigem,dfFantasma],ignore_index=True)

        return arrOrigem

    def _process_hosDf(self,colName):

        patDfPos = self.dffPaciente.groupby(by=[colName,'DT_INTER','CNES']).agg({'N_AIH':'count'}).reset_index()
        patDfNeg = self.dffPaciente.groupby(by=[colName,'DT_SAIDA','CNES']).agg({'N_AIH':'count'}).reset_index()

        releaseDf = self.dffPaciente[[colName,'DT_SAIDA','DT_INTER','CNES','N_AIH']]

        releaseDf = releaseDf[(releaseDf['DT_INTER'] < self.initialTime) &
                              (((releaseDf['DT_SAIDA'] < self.finialTime) &
                               (releaseDf['DT_SAIDA'] > self.initialTime)))]

        releaseDf = releaseDf.groupby(by=[colName,'DT_SAIDA','CNES']).agg({'N_AIH':'count'}).reset_index()
        releaseDf.rename(columns={'N_AIH':'QTD_RELEASE'},inplace=True)

        dfResample = pd.concat([self.dffPaciente[[colName,'DT_INTER','CNES']].rename(columns={'DT_INTER':'DT_SAIDA'}),
                                 self.dffPaciente[[colName,'DT_SAIDA','CNES']]
                                ]).drop_duplicates()

        patDfPos.rename(columns={'N_AIH':'QTD_POS'},inplace=True)
        patDfNeg.rename(columns={'N_AIH':'QTD_NEG'},inplace=True)

        dfResample = dfResample.merge(patDfPos,how='left',left_on=['DT_SAIDA',colName,'CNES'],right_on=['DT_INTER',colName,'CNES'])
        dfResample = dfResample.merge(patDfNeg,how='left',left_on=['DT_SAIDA',colName,'CNES'],right_on=['DT_SAIDA',colName,'CNES'])

        dfResample = dfResample[(dfResample['QTD_POS'].notnull()) | (dfResample['QTD_NEG'].notnull())]
        dfResample['QTD_POS'] = dfResample['QTD_POS'].fillna(0)
        dfResample['QTD_NEG'] = dfResample['QTD_NEG'].fillna(0)

        dfResample = dfResample[['DT_SAIDA','CNES',colName,'QTD_POS','QTD_NEG']]
        dfResample.rename(columns={'DT_SAIDA':'DATA'},inplace=True)
        dfResample['QTD_NET'] = dfResample['QTD_POS'] - dfResample['QTD_NEG']
        dfResample.sort_values(by=['DATA','CNES',colName],inplace=True)
        dfResample['QTD_ACU'] = dfResample.groupby(['CNES',colName])['QTD_NET'].cumsum()

        dfResample = dfResample.merge(releaseDf,how='left',left_on=['DATA','CNES',colName],right_on=['DT_SAIDA','CNES',colName])
        dfResample.drop(columns=['DT_SAIDA'],inplace=True)
        dfResample['QTD_RELEASE'] = dfResample['QTD_RELEASE'].fillna(0)

        todosPatTipo = dfResample[[colName]].drop_duplicates()
        todosCnes = dfResample[['CNES']].drop_duplicates()
        todosDatas = dfResample[['DATA']].drop_duplicates()

        todosPatTipo['key'] = 0 #cross join gamb
        todosCnes['key'] = 0 #cross join gamb
        todosDatas['key'] = 0 #cross join gamb

        allDims = todosPatTipo.merge(todosCnes, on='key',how='outer')
        allDims = allDims.merge(todosDatas, on='key',how='outer')
        allDims.drop(columns=['key'],inplace=True)

        dfResample = allDims.merge(dfResample, how='left', on=[colName,'CNES','DATA'])

        dfResample = dfResample[['DATA','CNES',colName,'QTD_POS','QTD_NEG','QTD_NET','QTD_ACU','QTD_RELEASE']]

        dfResample.sort_values(by=['DATA','CNES',colName],inplace=True)

        dfResample.update(dfResample.groupby(by=['CNES',colName])[['QTD_ACU']].ffill().fillna(0))

        dfResample['QTD_POS'] = dfResample['QTD_POS'].fillna(0)
        dfResample['QTD_NEG'] = dfResample['QTD_NEG'].fillna(0)
        dfResample['QTD_NET'] = dfResample['QTD_NET'].fillna(0)
        dfResample['QTD_RELEASE'] = dfResample['QTD_RELEASE'].fillna(0)

        dfAjusteEquip = dfResample[(dfResample[colName]=='CANCER_CIRURGIA') | (dfResample[colName]=='CANCER_CLINICOS')]
        dfAjusteEquip = dfAjusteEquip.groupby(by=['CNES',colName]).agg({'QTD_ACU':'max'}).reset_index()
        dfAjusteEquip = dfAjusteEquip[dfAjusteEquip['QTD_ACU']>0]
        dfAjusteEquip.rename(columns={'QTD_ACU':'QTD_SUS_AJ'},inplace=True)

        dfResample = dfResample[(dfResample['DATA']>=self.initialTime) & (dfResample['DATA']<self.finialTime)]

        #juntar esse dfResample com o hosDf x todos os dias x todas as doenças[equip], backfill e foward fill, e tchau.

        #dfResample = dfResample[(dfResample['DATA']>=self.initialTime) & (dfResample['DATA']<self.finialTime)]

        return dfResample, dfAjusteEquip

    def _process_equipDf(self):

        dfEquip =  self.dfdLeiPath[['CNES','DESC_LEITO','QT_SUS','COMPETEN']]
        dfEquip['datetime'] = pd.to_datetime(dfEquip['COMPETEN'], format='%Y%m')
        dfEquip.drop(columns=['COMPETEN'],inplace=True)

        dfEquip=dfEquip.groupby(by=['datetime','DESC_LEITO','CNES']).agg({'QT_SUS':'sum'}).reset_index()

        dfResample = pd.date_range(start=datetime.strptime(str(self.initialTime), '%Y%m%d'),end=datetime.strptime(str(self.finialTime), '%Y%m%d'),freq='D')
        dfResample = pd.DataFrame(dfResample.values.reshape(len(dfResample),1),columns=['exp_date'])
        dfResample['datetime'] = dfResample['exp_date'].dt.year.astype(str) + "-" + dfResample['exp_date'].dt.month.astype(str) + '-01'
        dfResample['datetime'] = pd.to_datetime(dfResample['datetime'])
        
        dfEquip = dfEquip.merge(dfResample,on='datetime')
        dfEquip.drop(columns=['datetime'],inplace=True)
        dfEquip.rename(columns={'exp_date':'DATA'},inplace=True)

        dfEquip = dfEquip[['CNES','DESC_LEITO','QT_SUS','DATA']].drop_duplicates()

        dfEquip = dfEquip[dfEquip['QT_SUS']>0] 

        dfEquip['DATA'] = dfEquip['DATA'].apply(lambda row: row.year*10000+row.month*100+row.day)

        return dfEquip

    def _create_prof_data(self):

        dffProfission =  self.dffProfission
        dffProfission['datetime'] = pd.to_datetime(dffProfission['COMPETEN'], format='%Y%m')
        dffProfission.drop(columns=['COMPETEN'],inplace=True)

        dfResample = pd.date_range(start=datetime.strptime(str(self.initialTime), '%Y%m%d'),end=datetime.strptime(str(self.finialTime), '%Y%m%d'),freq='D')
        dfResample = pd.DataFrame(dfResample.values.reshape(len(dfResample),1),columns=['exp_date'])
        dfResample['datetime'] = dfResample['exp_date'].dt.year.astype(str) + "-" + dfResample['exp_date'].dt.month.astype(str) + '-01'
        dfResample['datetime'] = pd.to_datetime(dfResample['datetime'])
        
        dffProfission = dffProfission.merge(dfResample,on='datetime')
        dffProfission.drop(columns=['datetime'],inplace=True)
        dffProfission.rename(columns={'exp_date':'DATA'},inplace=True)

        ##fantasma:
        ghostHospList = [[0] * len(dffProfission)]
        nomCbo = ['Médico'] * len(dffProfission)
        datas = dffProfission['DATA'].tolist()
        maxDistList = [999999] * len(dffProfission)
        maxCboQtyList = [999999] * len(dffProfission)

        ghostHospList.append(nomCbo)
        ghostHospList.append(maxDistList)
        ghostHospList.append(maxCboQtyList)
        ghostHospList.append(datas)

        ghostDfNP2d = np.array(ghostHospList).T

        dfFantasma = pd.DataFrame(ghostDfNP2d,columns=['CNES','Nome_Cbo','HORAS','CBO','DATA'])
        dfFantasma['CNES'] = dfFantasma['CNES'].astype(int)
        dfFantasma['HORAS'] = dfFantasma['HORAS'].astype(int)
        dfFantasma['CBO'] = dfFantasma['CBO'].astype(int)

        dfFantasma = dfFantasma.drop_duplicates()

        dffProfission = pd.concat([dffProfission,dfFantasma],ignore_index=True)
        ###
        dffProfission['DATA'] = dffProfission['DATA'].apply(lambda row: row.year*10000+row.month*100+row.day)

        ##simplificacao: pegar QLP total:

        dffProfQty = dffProfission.groupby(by=['CNES','DATA']).agg({'CBO':'sum'}).reset_index()
        dffProfQty.rename(columns={'CBO':'QTY'},inplace=True)

        dffProfHrs = dffProfission.groupby(by=['CNES','HORAS','DATA']).agg({'CBO':'sum'}).reset_index()
        dffProfHrs['QTY'] = dffProfHrs['HORAS']*dffProfHrs['CBO']
        dffProfHrs = dffProfHrs.groupby(by=['CNES','DATA']).agg({'QTY':'sum'}).reset_index()

        return dffProfQty, dffProfHrs

    def _process_patDf(self):

        df = self.dffPaciente[['DT_INTER','MUNIC_RES','TP_PAC_AGRP']]

        dfMediaStay = self.dffPaciente.groupby(by=['TP_PAC_AGRP']).agg({'DIAS_PERM':'mean'}).reset_index()
        dfMediaStay['DIAS_PERM'] = round(dfMediaStay['DIAS_PERM'],0).astype(int)

        df = self.dffPaciente.groupby(by=['DT_INTER','MUNIC_RES','TP_PAC_AGRP']).agg({'N_AIH':'count'}).reset_index()
        
        df = df.merge(dfMediaStay,on=['TP_PAC_AGRP'])
        df.rename(columns={'N_AIH':'QTY','DIAS_PERM':'MED_PERM'},inplace=True)

        #df = df[(df['DT_INTER']>=self.initialTime) & (df['DT_INTER']<self.finialTime)]

        return df

    def _create_real_patdf(self):

        df = self.dffPaciente[['DT_INTER','MUNIC_MOV','MUNIC_RES','TP_PAC_AGRP']]
        
        df = self.dffPaciente.groupby(by=['DT_INTER','MUNIC_RES','MUNIC_MOV','TP_PAC_AGRP']).agg({'N_AIH':'count'}).reset_index()
        
        df.rename(columns={'N_AIH':'QTY'},inplace=True)

        latLong = self.dfLatLong[['codigo_ibge','latitude','longitude']]

        latLong['codigo_ibge'] = latLong['codigo_ibge'].apply(lambda row: int(str(row)[:-1]))

        df = df.merge(latLong, how='inner', left_on='MUNIC_MOV',right_on='codigo_ibge')
        df.rename(columns={'latitude':'latitude_dest','longitude':'longitude_dest'},inplace=True)
        df.drop(columns=['codigo_ibge'],inplace=True)
        df = df.merge(latLong, how='inner', left_on='MUNIC_RES',right_on='codigo_ibge')
        df.rename(columns={'latitude':'latitude_ori','longitude':'longitude_ori'},inplace=True)
        df.drop(columns=['codigo_ibge'],inplace=True)

        df['DIST'] = df.apply(lambda row: distance_latLong(row['latitude_ori'],row['longitude_ori'],row['latitude_dest'],row['longitude_dest']),axis=1)
        df['DIST'] = df['DIST'].astype(int)
        df.drop(columns=['latitude_ori','longitude_ori','latitude_dest','longitude_dest'],inplace=True)
        df['Weight'] = df['QTY']
        df.drop(columns=['QTY'],inplace=True)

        df.rename(columns={'MUNIC_RES':'Source','MUNIC_MOV':'Target'},inplace=True)

        nodeDf = latLong[['codigo_ibge','latitude','longitude']].drop_duplicates()

        nodeDf.rename(columns={'codigo_ibge':'Id'},inplace=True)

        df['ESTAMPA_DO_TEMPO'] = pd.to_datetime(df['DT_INTER'], format='%Y%m%d')

        df['ESTADO'] = df['Source'].apply(lambda row: int(str(row)[0:2])).astype(int)
        df = df[df['ESTADO']==23]
        df.drop(columns=['ESTADO'],inplace=True)
        df = df[~df['Source'].isin([231260,231085,231025,231020,230970,230960,230770,230765,230625,230523,230495,230440,230428,230395,230370,230350,230100])]

        #df = df[df['DT_INTER']>=20]

        df = df.groupby(by=['DT_INTER','Source','Target','TP_PAC_AGRP','ESTAMPA_DO_TEMPO','DIST']).agg({'Weight':'sum'}).reset_index()

        nodeDf = nodeDf[nodeDf['Id'].isin(np.unique(df['Source'].tolist()+df['Target'].tolist()))]

        df.to_csv('/mnt/d/Projetos/healthgraphopt/edgelist.csv',index=False)
        nodeDf.to_csv('/mnt/d/Projetos/healthgraphopt/nodeList.csv',index=False)

        return None

#teste = graph_data(initialTime=20210101,durationTime=8)

    def _create_bi_data_host_ocu(self):

        df = self.dffPaciente[['DT_INTER','CNES','TP_DOENCA']]
        df['QTY'] = 1

        df_outros = df[df['TP_DOENCA']=='OUTROS']
        df_covid = df[df['TP_DOENCA']=='COVID']
        df_cancer = df[df['TP_DOENCA']=='CANCER']

        df_outros = df_outros.groupby(by=['DT_INTER','CNES']).agg({'QTY':'sum'}).reset_index()
        df_outros.rename(columns={'QTY':'QTY_OUTROS'},inplace=True)
        df_covid = df_covid.groupby(by=['DT_INTER','CNES']).agg({'QTY':'sum'}).reset_index()
        df_covid.rename(columns={'QTY':'QTY_COVID'},inplace=True)
        df_cancer = df_cancer.groupby(by=['DT_INTER','CNES']).agg({'QTY':'sum'}).reset_index()
        df_cancer.rename(columns={'QTY':'QTY_CANCER'},inplace=True)

        df = df[['DT_INTER','CNES']].drop_duplicates()

        df = df.merge(df_outros,how='left',on=['DT_INTER','CNES'])
        df = df.merge(df_covid,how='left',on=['DT_INTER','CNES'])
        df = df.merge(df_cancer,how='left',on=['DT_INTER','CNES'])

        df.fillna(0,inplace=True)

        df = df.astype(int)

        df['QTY_TOTAL'] = df['QTY_OUTROS'] + df['QTY_COVID'] + df['QTY_CANCER']

        df.to_csv(os.path.join(self.curDir,'data','external','ocupacao_hosp_real_BI.csv'),index=False)

        return None