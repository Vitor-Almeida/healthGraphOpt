import pandas as pd
import os
import numpy as np
from utils import distance_latLong, time_delta
import itertools
import pickle


def fix_initial_cap(row):

    if row['CNES'] != 0 :
        if row['QT_SUS'] <= row['QTD_ACU']+row['RELEASE_MAX']: #row['RELEASE_MAX'] nao tava precisando
            row['QT_SUS'] = row['QTD_ACU']+row['RELEASE_MAX']

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
                                       usecols=['N_AIH','UF_ZI','ESPEC','ANO_CMPT','MES_CMPT','MUNIC_RES',
                                                'NASC','SEXO','DT_INTER','DT_SAIDA','DIAS_PERM','DIAG_PRINC','DIAG_SECUN',
                                                'CNES','MUNIC_MOV','IDADE','MORTE','UTI_MES_TO','MARCA_UTI',
                                                'PROC_SOLIC','PROC_REA','HOMONIMO','CID_ASSO','CID_MORTE',
                                                'COMPLEX','MARCA_UCI','DIAGSEC1','TPDISEC1','DIAGSEC2','TPDISEC2'])

        self.dfdHosPath = pd.read_csv(dHosPath, #nao tem o nome do hospital
                                      sep=",",
                                      encoding='latin',
                                      usecols=['CNES','CODUFMUN','VINC_SUS','TURNO_AT','TP_UNID','DT_EXPED',
                                               'QTLEITP1','QTLEITP2','QTLEITP3','LEITHOSP','ATENDAMB','CENTROBS',
                                               'CENTRCIR','URGEMERG','CENTRNEO','ATENDHOS','DT_ATUAL','COMPETEN'])

        self.dfdEquipPath = pd.read_csv(dEquipPath, #nao tem o nome dos equipamento, tem que pesquisar
                                        sep=",",
                                        encoding='latin',
                                        usecols=['CNES','TIPEQUIP','CODEQUIP','QT_EXIST','QT_USO','IND_SUS','IND_NSUS',
                                                 'COMPETEN','TERCEIRO'])

        self.dfdLeiPath = pd.read_csv(dLeiPath,
                                      sep=",",
                                      encoding='latin',
                                      usecols=['CNES','TP_LEITO','CODLEITO','QT_EXIST','QT_CONTR','QT_SUS','COMPETEN'])

        self.dfLatLong = pd.read_csv(dfLatLongPath,
                                     sep=",",
                                     encoding="latin")

        self.initialTime = initialTime
        self.durationTime = durationTime
        self.finialTime = time_delta(self.initialTime,+self.durationTime)

        odDf = self._create_od_matrix()
        patDf = self._process_patDf()
        equipDf = self._process_equipDf()
        hospDf = self._process_hosDf() #ta saindo da tabela real, teria que puxar da tabela de estabelecimento mesmo. Isso aqui é a tabela de demanda/release, nao é dimhosp

        #minTime = time_delta(initialTime,-max(patDf[(patDf['DT_INTER']>=self.initialTime) & (patDf['DT_INTER']<self.finialTime)]['MED_PERM'])) #tempo minimo pra pegar a LOS[p]
        #patDf = patDf[(patDf['DT_INTER']>=minTime) & (patDf['DT_INTER']<self.finialTime)]
        #hospDf = hospDf[(hospDf['DATA']>=minTime) & (hospDf['DATA']<self.finialTime)]

        patDf = patDf[(patDf['DT_INTER']>=self.initialTime) & (patDf['DT_INTER']<self.finialTime)]
        hospDf = hospDf[(hospDf['DATA']>=self.initialTime) & (hospDf['DATA']<self.finialTime)]

        ### simplificacoes que nao vao estar na versao final:
        hospSIMPLIFICADO,encodingDf = self._simp_doenca_equip(equipDf,hospDf)

        hospSIMPLIFICADO = self._create_ghost_hosp(hospSIMPLIFICADO)

        patDfSIMPLIFICADO = patDf.merge(encodingDf,how='inner',on='DIAG_PRINC')
        patDfSIMPLIFICADO.drop(columns='DIAG_PRINC',inplace=True)

        odDf=odDf[odDf['MUNIC_RES'].isin(patDfSIMPLIFICADO['MUNIC_RES'])]
        odDf=odDf[odDf['CNES'].isin(hospSIMPLIFICADO['CNES'])]

        #### Super simplificacoes (redução do tam)############################:

        topNHos = hospSIMPLIFICADO.groupby(by=['CNES']).agg({'QT_SUS':'sum'}).reset_index()
        topNHos.sort_values(by=['QT_SUS'],inplace=True,ascending=False)
        topNHos = topNHos['CNES'][:7]

        hospSIMPLIFICADO=hospSIMPLIFICADO[hospSIMPLIFICADO['CNES'].isin(topNHos)]

        topNPac = patDfSIMPLIFICADO.groupby(by=['MUNIC_RES']).agg({'QTY':'sum'}).reset_index()
        topNPac.sort_values(by=['QTY'],inplace=True,ascending=False)
        topNPac = topNPac['MUNIC_RES'][:7]

        patDfSIMPLIFICADO=patDfSIMPLIFICADO[patDfSIMPLIFICADO['MUNIC_RES'].isin(topNPac)]

        odDf=odDf[odDf['MUNIC_RES'].isin(patDfSIMPLIFICADO['MUNIC_RES'])]
        odDf=odDf[odDf['CNES'].isin(hospSIMPLIFICADO['CNES'])]

        ##################################################################

        #### correções ####################################################

        #patDfSIMPLIFICADO['MED_PERM'] = 1
        #hospSIMPLIFICADO['QTD_RELEASE'] = 0

        relSum = hospSIMPLIFICADO.groupby(by=['CNES','TP_LEITO']).agg({'QTD_RELEASE':'sum'}).reset_index()
        relSum.rename(columns={'QTD_RELEASE':'RELEASE_MAX'},inplace=True)
        hospSIMPLIFICADO = hospSIMPLIFICADO.merge(relSum,how='left',left_on=['CNES','TP_LEITO'],right_on=['CNES','TP_LEITO'])

        hospSIMPLIFICADO = hospSIMPLIFICADO.apply(fix_initial_cap,axis=1) #ajustando para capacidade inicial >= pat inicial + release do periodo
        hospSIMPLIFICADO.drop(columns=['RELEASE_MAX'],inplace=True)

        #hospSIMPLIFICADO['QTD_ACU'] = hospSIMPLIFICADO['QTD_ACU'] + 500  # nao pode ter releasett > qtd inicial para nenhuma combinação !!!
        #hospSIMPLIFICADO['QT_SUS'] = 99999 # tem que garantir aqui q tenha capacidade inicial >= demanda inicial

        ##################################################################

        #hospSIMPLIFICADO.to_csv('cu3.csv')
        #patDfSIMPLIFICADO.to_csv('demanda.csv')

        #fazer df com o grafo real
        #olhar os filtros, colunas, pedir pra epdimo olhar os conjutos de doença e equipamento.
        #fazer um parametro xN pra aumentar capacidade e reduzir demanda.
        #desenhar output /  input, colocar no git antes de ficar pronto.

        odDf.set_index(['MUNIC_RES','CNES'],inplace=True)

        dffDemanda = patDfSIMPLIFICADO.groupby(by=['DT_INTER','MUNIC_RES','TP_LEITO']).agg({'QTY':'sum'}).reset_index()
        dffDemanda.set_index(['TP_LEITO','MUNIC_RES','DT_INTER'],inplace=True)
  
        dfCONcapacity = hospSIMPLIFICADO.groupby(by=['CNES','TP_LEITO']).agg({'QT_SUS':'max'}).reset_index()
        dfCONcapacity.set_index(['TP_LEITO','CNES'],inplace=True)

        dfInitPatientsph = hospSIMPLIFICADO[['CNES','TP_LEITO','QTD_ACU']].drop_duplicates(keep='first')
        dfInitPatientsph.set_index(['TP_LEITO','CNES'],inplace=True)

        dfReleasePatt = hospSIMPLIFICADO[['DATA','CNES','TP_LEITO','QTD_RELEASE']]
        dfReleasePatt.set_index(['TP_LEITO','CNES','DATA'],inplace=True)

        dfAvgLenStay = patDfSIMPLIFICADO[['TP_LEITO','MED_PERM']].drop_duplicates()
        dfAvgLenStay.set_index(['TP_LEITO'],inplace=True)

        self.patTypeList = patDfSIMPLIFICADO['TP_LEITO'].drop_duplicates().tolist()
        self.patTypeList.sort()
        self.equipIdList = hospSIMPLIFICADO['TP_LEITO'].drop_duplicates().tolist()
        self.equipIdList.sort()

        self.areaIdList = patDfSIMPLIFICADO['MUNIC_RES'].drop_duplicates().tolist()
        self.hosIdList = hospSIMPLIFICADO['CNES'].drop_duplicates().tolist()

        self.tList = [time_delta(self.initialTime,+n) for n in range(self.durationTime)]

        self.Demandpat = {index:row['QTY'] for index, row in dffDemanda.iterrows()}

        self.CONCapacityrh  = {index:row['QT_SUS'] for index, row in dfCONcapacity.iterrows()} 

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

        return None

    def _create_ghost_hosp(self,hospDf:pd.DataFrame):


        allDates = hospDf['DATA'].drop_duplicates().tolist()
        allEquip = hospDf['TP_LEITO'].drop_duplicates().tolist()

        prods = itertools.product(allDates,allEquip)
        ghostDfNP2d = []

        for n in prods:
            ghostDfNP2d.append([n[0],n[1],99999999,0,0,0,0,0,0])

        dfFantasma = pd.DataFrame(ghostDfNP2d,columns=['DATA','TP_LEITO','QT_SUS','CNES','QTD_POS','QTD_NEG','QTD_NET','QTD_ACU','QTD_RELEASE'])
        #dfFantasma['DATA'] = dfFantasma['DATA'].astype(int)
        #dfFantasma['CNES'] = dfFantasma['CNES'].astype(int)
        #dfFantasma['QT_SUS'] = dfFantasma['QT_SUS'].astype(int)

        dfFantasma = dfFantasma[['DATA','CNES','QTD_POS','QTD_NEG','QTD_NET','QTD_ACU','QTD_RELEASE','TP_LEITO','QT_SUS']]

        dfFantasma = pd.concat([hospDf,dfFantasma],ignore_index=True)

        dfFantasma = dfFantasma.astype(int)

        ######

        return dfFantasma

    def _simp_doenca_equip(self,equipDf:pd.DataFrame,hospDf:pd.DataFrame) -> pd.DataFrame:

        diags = hospDf.groupby(by=['DIAG_PRINC']).agg({'QTD_POS':'sum'}).reset_index()
        diags.sort_values(by=['QTD_POS'],inplace=True,ascending=False)
        diags = diags['DIAG_PRINC'][:7]
        encd = [[1,2,3,4,5,6,7]]
        encd.append(list(diags))
        arr = np.array(encd).T
        encodingDf = pd.DataFrame(arr,columns=['TP_LEITO','DIAG_PRINC'])
        encodingDf['TP_LEITO'] = encodingDf['TP_LEITO'].astype(int)

        hospDf = hospDf.merge(encodingDf,how='inner',on='DIAG_PRINC')
        hospDf.drop(columns=['DIAG_PRINC'],inplace=True)

        hospDf = hospDf.merge(equipDf,how='left',on=['TP_LEITO','CNES'])
        hospDf['QT_SUS'] = hospDf['QT_SUS'].fillna(0)
        hospDf['QT_SUS'] = hospDf['QT_SUS'].astype(int)

        hospDf = hospDf[hospDf['QT_SUS']>0]

        return hospDf,encodingDf

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

        patDfPos = self.dffPaciente.groupby(by=['DIAG_PRINC','DT_INTER','CNES']).agg({'N_AIH':'count'}).reset_index()
        patDfNeg = self.dffPaciente.groupby(by=['DIAG_PRINC','DT_SAIDA','CNES']).agg({'N_AIH':'count'}).reset_index()

        releaseDf = self.dffPaciente[['DIAG_PRINC','DT_SAIDA','DT_INTER','CNES','N_AIH']]

        releaseDf = releaseDf[(releaseDf['DT_INTER'] < self.initialTime) &
                              (((releaseDf['DT_SAIDA'] < self.finialTime) &
                               (releaseDf['DT_SAIDA'] > self.initialTime)))]

        releaseDf = releaseDf.groupby(by=['DIAG_PRINC','DT_SAIDA','CNES']).agg({'N_AIH':'count'}).reset_index()
        releaseDf.rename(columns={'N_AIH':'QTD_RELEASE'},inplace=True)

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

        dfResample = dfResample.merge(releaseDf,how='left',left_on=['DATA','CNES','DIAG_PRINC'],right_on=['DT_SAIDA','CNES','DIAG_PRINC'])
        dfResample.drop(columns=['DT_SAIDA'],inplace=True)
        dfResample['QTD_RELEASE'] = dfResample['QTD_RELEASE'].fillna(0)

        #dfResample = dfResample[(dfResample['DATA']>=self.initialTime) & (dfResample['DATA']<self.finialTime)]

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

        #df = df[(df['DT_INTER']>=self.initialTime) & (df['DT_INTER']<self.finialTime)]

        return df

#teste = graph_data(initialTime=20210101,durationTime=8)