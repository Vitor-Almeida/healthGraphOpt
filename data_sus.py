import pandas as pd
import os
import numpy as np
from utils import distance_latLong, time_delta, _normalize_demand
import itertools
import pickle
from deParas import _load_deparas, encoding_patType, _create_dyn_qtd

def fix_initial_cap(row):

    if row['CNES'] != 0 :
        if row['QT_SUS'] <= row['QTD_ACU'] + row['RELEASE_MAX']: #row['RELEASE_MAX'] nao tava precisando
            row['QT_SUS'] = row['QTD_ACU'] + row['RELEASE_MAX']

    #if row['CNES'] != 0 :
    #    row['QT_SUS'] = 1235

    #if row['CNES'] == 6848710:
    #    row['QT_SUS'] = 140

    return row

class graph_data():

    def __init__(self,initialTime,durationTime):

        curDir = os.path.dirname(os.path.realpath(__file__))

        fPatPath = os.path.join(curDir,'data','raw','SIH_CE.csv')
        dHosPath = os.path.join(curDir,'data','raw','ST_CNES_CE.csv')
        dEquipPath = os.path.join(curDir,'data','raw','EQ_CNES_CE.csv')
        dLeiPath = os.path.join(curDir,'data','raw','LT_CNES_CE.csv')
        dfLatLongPath = os.path.join(curDir,'data','external','latlongMun.csv')

        self.dffPaciente = pd.read_csv(fPatPath,
                                       sep=",",
                                       encoding='latin',
                                       usecols=['N_AIH','UF_ZI','ESPEC','ANO_CMPT','MES_CMPT','MUNIC_RES','PROC_REA',
                                                'NASC','SEXO','DT_INTER','DT_SAIDA','DIAS_PERM','DIAG_PRINC','DIAG_SECUN',
                                                'CNES','MUNIC_MOV','IDADE','MORTE','UTI_MES_TO','MARCA_UTI',
                                                'PROC_SOLIC','PROC_REA','HOMONIMO','CID_ASSO','CID_MORTE',
                                                'COMPLEX','MARCA_UCI','DIAGSEC1','TPDISEC1','DIAGSEC2','TPDISEC2'])

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

        self.initialTime = initialTime
        self.durationTime = durationTime
        self.finialTime = time_delta(self.initialTime,+self.durationTime)

        self.dffPaciente, self.dfdLeiPath, dfDemandaCancer = _load_deparas(self.dffPaciente,self.dfdLeiPath)

        #--> primeira coisa pra fazer é a capacidade dinamica. e o normalize_demanda
        #depois, poca tudo que nao é cancer, e segue normal.

        odDf = self._create_od_matrix() #sai do real também, nao era pra sair do real, talvez rodar ela antes do filtro da data.
        self._create_real_patdf() #exportar csvs para o gephi no windows.
        patDf = self._process_patDf() #junta a média da stay
        equipDf = self._process_equipDf()
        hospDf = self._process_hosDf() #ta saindo da tabela real, teria que puxar da tabela de estabelecimento mesmo. Isso aqui é a tabela de demanda/release, nao é dimhosp, tem q no minimo fazer a permutação total CNES vs DIA

        patDf = patDf[(patDf['DT_INTER']>=self.initialTime) & (patDf['DT_INTER']<self.finialTime)]
        hospDf = hospDf[(hospDf['DATA']>=self.initialTime) & (hospDf['DATA']<self.finialTime)]

        dfDemandaCancer = _normalize_demand(dfDemandaCancer,np.unique(patDf['DT_INTER']))

        #fazer esse join em outro lugar:
        #colocar inner aq:
        hospDf = hospDf.merge(equipDf, how='left', left_on=['TP_PAC_AGRP','CNES'], right_on=['DESC_LEITO','CNES']) #olhar os NAN!
        hospDf.drop(columns=['DESC_LEITO'],inplace=True)
        hospDf = hospDf[hospDf['QT_SUS']>0] #aqui ta tirando os NAN
        hospDf = self._create_ghost_hosp(hospDf)

        ##encoding do tipo de paciente:
        patDf,hospDf,dfDemandaCancer,encdF = encoding_patType(patDf,hospDf,dfDemandaCancer)

        odDf=odDf[odDf['MUNIC_RES'].isin(patDf['MUNIC_RES'])]
        odDf=odDf[odDf['CNES'].isin(hospDf['CNES'])]

        #### correções de dados gov #####################################

        #patDfSIMPLIFICADO['MED_PERM'] = 1
        #hospSIMPLIFICADO['QTD_RELEASE'] = 0

        relSum = hospDf.groupby(by=['CNES','TP_PAC_AGRP']).agg({'QTD_RELEASE':'sum'}).reset_index()
        relSum.rename(columns={'QTD_RELEASE':'RELEASE_MAX'},inplace=True)
        hospDf = hospDf.merge(relSum,how='left',left_on=['CNES','TP_PAC_AGRP'],right_on=['CNES','TP_PAC_AGRP'])

        hospDf = hospDf.apply(fix_initial_cap,axis=1) #ajustando para capacidade inicial >= pat inicial + release do periodo
        hospDf.drop(columns=['RELEASE_MAX'],inplace=True)

        #hospSIMPLIFICADO['QTD_ACU'] = hospSIMPLIFICADO['QTD_ACU'] + 500  # nao pode ter releasett > qtd inicial para nenhuma combinação !!!
        #hospSIMPLIFICADO['QT_SUS'] = 99999 # tem que garantir aqui q tenha capacidade inicial >= demanda inicial

        ##################################################################

        ### criar hospDf com equip sendo alterado ###############:

        CancerhospDf, patCovidReal = _create_dyn_qtd(hospDf,encdF)

        patCovidReal.set_index(['DATA','CNES'],inplace=True)
        CancerhospDf.set_index(['DATA','CNES','TP_PAC_AGRP'],inplace=True)

        ##########################################################

        odDf.set_index(['MUNIC_RES','CNES'],inplace=True)

        dffDemanda = patDf.groupby(by=['DT_INTER','MUNIC_RES','TP_PAC_AGRP']).agg({'QTY':'sum'}).reset_index()
        dffDemanda.set_index(['TP_PAC_AGRP','MUNIC_RES','DT_INTER'],inplace=True)

        dfDemandaCancer.set_index(['TP_PAC_AGRP','MUNIC_RES','DT_INTER'],inplace=True)
  
        dfCONcapacity = hospDf.groupby(by=['CNES','TP_PAC_AGRP']).agg({'QT_SUS':'max'}).reset_index()
        dfCONcapacity.set_index(['TP_PAC_AGRP','CNES'],inplace=True)

        dfInitPatientsph = hospDf[['CNES','TP_PAC_AGRP','QTD_ACU']][hospDf['DATA']==min(hospDf['DATA'])].drop_duplicates()
        dfInitPatientsph.set_index(['TP_PAC_AGRP','CNES'],inplace=True)

        dfReleasePatt = hospDf[['DATA','CNES','TP_PAC_AGRP','QTD_RELEASE']]
        dfReleasePatt.set_index(['TP_PAC_AGRP','CNES','DATA'],inplace=True)

        dfAvgLenStay = patDf[['TP_PAC_AGRP','MED_PERM']].drop_duplicates()
        dfAvgLenStay.set_index(['TP_PAC_AGRP'],inplace=True)

        self.patTypeList = patDf['TP_PAC_AGRP'].drop_duplicates().tolist()
        self.patTypeList.sort()
        self.equipIdList = hospDf['TP_PAC_AGRP'].drop_duplicates().tolist()
        self.equipIdList.sort()

        self.areaIdList = patDf['MUNIC_RES'].drop_duplicates().tolist()
        self.hosIdList = hospDf['CNES'].drop_duplicates().tolist()

        self.tList = [time_delta(self.initialTime,+n) for n in range(self.durationTime)]

        self.qtdCovidReal = {index:row['QTD_ACU'] for index, row in patCovidReal.iterrows()}

        self.Demandpat = {index:row['QTY'] for index, row in dffDemanda.iterrows()}

        self.DemandCancerpat = {index:row['QTY'] for index, row in dfDemandaCancer.iterrows()}

        self.CONCapacityrh  = {index:row['QT_SUS'] for index, row in dfCONcapacity.iterrows()} 

        self.CONCapacityrhCancer  = {index:row['QT_SUS'] for index, row in CancerhospDf.iterrows()}

        self.InitPatientsph  = {index:row['QTD_ACU'] for index, row in dfInitPatientsph.iterrows()} 

        self.releasePatientspht  = {index:row['QTD_RELEASE'] for index, row in dfReleasePatt.iterrows()}

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
        with open('./data/bin/Demandpat.pkl', 'wb') as f:
            pickle.dump(self.Demandpat, f)
            f.close()
        with open('./data/bin/CONCapacityrh.pkl', 'wb') as f:
            pickle.dump(self.CONCapacityrh, f)
            f.close()
        with open('./data/bin/InitPatientsph.pkl', 'wb') as f:
            pickle.dump(self.InitPatientsph, f)
            f.close()
        with open('./data/bin/releasePatientspht.pkl', 'wb') as f:
            pickle.dump(self.releasePatientspht, f)
            f.close()
        with open('./data/bin/LOSp.pkl', 'wb') as f:
            pickle.dump(self.LOSp, f)
            f.close()
        with open('./data/bin/Distanceah.pkl', 'wb') as f:
            pickle.dump(self.Distanceah, f)
            f.close()
        with open('./data/bin/CONCapacityrhCancer.pkl', 'wb') as f:
            pickle.dump(self.CONCapacityrhCancer, f)
            f.close()
        with open('./data/bin/qtdCovidReal.pkl', 'wb') as f:
            pickle.dump(self.qtdCovidReal, f)
            f.close()
        with open('./data/bin/DemandCancerpat.pkl', 'wb') as f:
            pickle.dump(self.DemandCancerpat, f)
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

    def _process_hosDf(self):

        #hosDf =  self.dffPaciente[['CNES','TP_LEITO','QT_SUS','COMPETEN']].drop_duplicates()

        patDfPos = self.dffPaciente.groupby(by=['TP_PAC_AGRP','DT_INTER','CNES']).agg({'N_AIH':'count'}).reset_index()
        patDfNeg = self.dffPaciente.groupby(by=['TP_PAC_AGRP','DT_SAIDA','CNES']).agg({'N_AIH':'count'}).reset_index()

        releaseDf = self.dffPaciente[['TP_PAC_AGRP','DT_SAIDA','DT_INTER','CNES','N_AIH']]

        releaseDf = releaseDf[(releaseDf['DT_INTER'] < self.initialTime) &
                              (((releaseDf['DT_SAIDA'] < self.finialTime) &
                               (releaseDf['DT_SAIDA'] > self.initialTime)))]

        releaseDf = releaseDf.groupby(by=['TP_PAC_AGRP','DT_SAIDA','CNES']).agg({'N_AIH':'count'}).reset_index()
        releaseDf.rename(columns={'N_AIH':'QTD_RELEASE'},inplace=True)

        dfResample = pd.concat([self.dffPaciente[['TP_PAC_AGRP','DT_INTER','CNES']].rename(columns={'DT_INTER':'DT_SAIDA'}),
                                 self.dffPaciente[['TP_PAC_AGRP','DT_SAIDA','CNES']]
                                ]).drop_duplicates()

        patDfPos.rename(columns={'N_AIH':'QTD_POS'},inplace=True)
        patDfNeg.rename(columns={'N_AIH':'QTD_NEG'},inplace=True)

        dfResample = dfResample.merge(patDfPos,how='left',left_on=['DT_SAIDA','TP_PAC_AGRP','CNES'],right_on=['DT_INTER','TP_PAC_AGRP','CNES'])
        dfResample = dfResample.merge(patDfNeg,how='left',left_on=['DT_SAIDA','TP_PAC_AGRP','CNES'],right_on=['DT_SAIDA','TP_PAC_AGRP','CNES'])

        dfResample = dfResample[(dfResample['QTD_POS'].notnull()) | (dfResample['QTD_NEG'].notnull())]
        dfResample['QTD_POS'] = dfResample['QTD_POS'].fillna(0)
        dfResample['QTD_NEG'] = dfResample['QTD_NEG'].fillna(0)

        dfResample = dfResample[['DT_SAIDA','CNES','TP_PAC_AGRP','QTD_POS','QTD_NEG']]
        dfResample.rename(columns={'DT_SAIDA':'DATA'},inplace=True)
        dfResample['QTD_NET'] = dfResample['QTD_POS'] - dfResample['QTD_NEG']
        dfResample.sort_values(by=['DATA','CNES','TP_PAC_AGRP'],inplace=True)
        dfResample['QTD_ACU'] = dfResample.groupby(['CNES','TP_PAC_AGRP'])['QTD_NET'].cumsum()

        dfResample = dfResample.merge(releaseDf,how='left',left_on=['DATA','CNES','TP_PAC_AGRP'],right_on=['DT_SAIDA','CNES','TP_PAC_AGRP'])
        dfResample.drop(columns=['DT_SAIDA'],inplace=True)
        dfResample['QTD_RELEASE'] = dfResample['QTD_RELEASE'].fillna(0)

        dfResample = dfResample.groupby(by=['DATA','CNES','TP_PAC_AGRP']).agg({'QTD_POS':'sum','QTD_NEG':'sum','QTD_NET':'sum','QTD_ACU':'sum','QTD_RELEASE':'sum'}).reset_index()

        #juntar esse dfResample com o hosDf x todos os dias x todas as doenças[equip], backfill e foward fill, e tchau.

        #dfResample = dfResample[(dfResample['DATA']>=self.initialTime) & (dfResample['DATA']<self.finialTime)]

        return dfResample

    def _process_equipDf(self):

        dfEquip =  self.dfdLeiPath[['CNES','DESC_LEITO','QT_SUS','COMPETEN']]
        dfEquip['datetime'] = pd.to_datetime(dfEquip['COMPETEN'], format='%Y%m')
        dfEquip.drop(columns=['COMPETEN'],inplace=True)

        dfEquip.groupby(by=['datetime','DESC_LEITO','CNES']).agg({'QT_SUS':'sum'}).reset_index()

        dfResample = pd.date_range(start=min(dfEquip['datetime']),end=max(dfEquip['datetime']),freq='D')
        dfResample = pd.DataFrame(dfResample.values.reshape(len(dfResample),1),columns=['exp_date'])
        dfResample['datetime'] = dfResample['exp_date'].dt.year.astype(str) + "-" + dfResample['exp_date'].dt.month.astype(str) + '-01'
        dfResample['datetime'] = pd.to_datetime(dfResample['datetime'])
        
        dfEquip = dfEquip.merge(dfResample,on='datetime')
        dfEquip.drop(columns=['datetime'],inplace=True)
        dfEquip.rename(columns={'exp_date':'DATA'},inplace=True)

        dfEquip = dfEquip.groupby(by=['CNES','DESC_LEITO']).agg({'QT_SUS':'max'}).reset_index()

        dfEquip = dfEquip[dfEquip['QT_SUS']>0] #duvida sobre a permutação ... o dic.get() é para resolver

        #deixar o periodo aqui depois de validar, pra deixar o leito por T também.

        return dfEquip

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
        df.drop(columns=['latitude_ori','longitude_ori','latitude_dest','longitude_dest'],inplace=True)
        df['Weight'] = df['QTY']
        df.drop(columns=['QTY'],inplace=True)

        df.rename(columns={'MUNIC_RES':'Source','MUNIC_MOV':'Target'},inplace=True)

        nodeDf = latLong[['codigo_ibge','latitude','longitude']].drop_duplicates()

        nodeDf.rename(columns={'codigo_ibge':'Id'},inplace=True)

        df['Timestamp'] = pd.to_datetime(df['DT_INTER'], format='%Y%m%d')

        df = df.groupby(by=['DT_INTER','Source','Target','TP_PAC_AGRP','Timestamp']).agg({'Weight':'sum'}).reset_index()

        nodeDf = nodeDf[nodeDf['Id'].isin(np.unique(df['Source'].tolist()+df['Target'].tolist()))]

        df.to_csv('/mnt/d/Projetos/healthgraphopt/edgelist.csv',index=False)
        nodeDf.to_csv('/mnt/d/Projetos/healthgraphopt/nodeList.csv',index=False)

        return None

#teste = graph_data(initialTime=20210101,durationTime=8)