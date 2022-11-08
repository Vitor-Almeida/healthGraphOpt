import os
import pandas as pd
import numpy as np

def _logica_fix_init(row,dfInitFix,dfCumSum):

    key0 = row['DATA']
    key1 = row['CNES']
    key2 = row['TP_PAC_AGRP']

    if dfInitFix.get((key1,key2),0) - dfCumSum.get((key0,key1,key2),0) < 0:
        print('error: RELEASE MAIOR QUE PACIENTES INICIAL NO PERIODO DE SIMULAÇÃO')
    else:
        if row['QT_SUS'] < dfInitFix.get((key1,key2),0) - dfCumSum.get((key0,key1,key2),0):
            row['QT_SUS'] = dfInitFix.get((key1,key2),0) - dfCumSum.get((key0,key1,key2),0)

    return row


def _logica_roubo_leito(row,qtdSusClinC,qtdSusCirC):

    usoCli = row['QT_ACU_USO_OUTROS_CLINICO']
    usoCir = row['QT_ACU_USO_OUTROS_CIRURGICO']

    if usoCli < 0:
        tmpQtdSusClincCancer = usoCli + row.loc[qtdSusClinC].sum()
        if tmpQtdSusClincCancer > 0:
            row['QT_SUS_DYN_CANCER_CLINICO'] = tmpQtdSusClincCancer
        else:
            row['QT_SUS_DYN_CANCER_CLINICO'] = 0
    if usoCir < 0:
        tmpQtdSusCirCancer = usoCir + row.loc[qtdSusCirC].sum()
        if tmpQtdSusCirCancer > 0:
            row['QT_SUS_DYN_CANCER_CIRURGICO'] = tmpQtdSusCirCancer
        else:
            row['QT_SUS_DYN_CANCER_CIRURGICO'] = 0

    return row

def _create_dyn_qtd(hospDf:pd.DataFrame,encdF:pd.DataFrame):

    nomesCancer = ['CANCER_CIRURGIA','CANCER_CLINICOS']
    encdF.set_index('IDX',inplace=True)

    codCancerCir = encdF[encdF['TP_PAC_AGRP']==nomesCancer[0]].index[0]
    codCancerCli = encdF[encdF['TP_PAC_AGRP']==nomesCancer[1]].index[0]
    
    newKeys = hospDf[['DATA','CNES']].drop_duplicates()
    newKeys.set_index(['DATA','CNES'],inplace=True)

    columnsZerarNan = []
    columnsRepetirNan = []
    dfVector = []

    for types in np.unique(hospDf['TP_PAC_AGRP']):
        tmpDf = hospDf[hospDf['TP_PAC_AGRP']==types]
        tmpDf.rename(columns={'QTD_POS':'QTD_POS_'+str(encdF.iloc[types,0])
                                ,'QTD_NEG':'QTD_NEG_'+str(encdF.iloc[types,0])
                                ,'QTD_NET':'QTD_NET_'+str(encdF.iloc[types,0])
                                ,'QTD_ACU':'QTD_ACU_'+str(encdF.iloc[types,0])
                                ,'QTD_RELEASE':'QTD_RELEASE_'+str(encdF.iloc[types,0])
                                ,'QT_SUS':'QT_SUS_'+str(encdF.iloc[types,0])
                                },inplace=True)
        tmpDf.drop(columns=['TP_PAC_AGRP'],inplace=True)
        tmpDf.set_index(['DATA','CNES'],inplace=True)
        dfVector.append(tmpDf)

        columnsZerarNan = columnsZerarNan + ['QTD_POS_'+str(encdF.iloc[types,0]), 'QTD_NEG_'+str(encdF.iloc[types,0]), 'QTD_NET_'+str(encdF.iloc[types,0]),
                                            'QTD_RELEASE_'+str(encdF.iloc[types,0])]

        columnsRepetirNan = columnsRepetirNan + ['QTD_ACU_'+str(encdF.iloc[types,0]), 'QT_SUS_'+str(encdF.iloc[types,0])]


    for df in dfVector:
        newKeys = newKeys.join(df)

    newKeys.reset_index(inplace=True)

    newKeys = newKeys.sort_values(by=['DATA','CNES'])

    newKeys.update(newKeys.groupby(by=['CNES'])[columnsRepetirNan].ffill().fillna(0))

    for cols in newKeys.columns:
        if cols in columnsZerarNan:
            newKeys[cols].fillna(0,inplace=True)

    newKeys['QT_ACU_CANCER_TT_REAL'] =  newKeys['QTD_ACU_CANCER_CIRURGIA'] + newKeys['QTD_ACU_CANCER_CLINICOS']
    newKeys['QT_ACU_OUTROS_TT_REAL'] =  newKeys['QTD_ACU_OUTROS_CIRURGIA'] + newKeys['QTD_ACU_OUTROS_CLINICOS']

    newKeys['QT_SUS_DYN_CANCER_CLINICO'] = newKeys['QT_SUS_CANCER_CLINICOS']
    newKeys['QT_SUS_DYN_CANCER_CIRURGICO'] = newKeys['QT_SUS_CANCER_CIRURGIA']

    newKeys['QT_ACU_USO_OUTROS_CLINICO'] = newKeys['QT_SUS_OUTROS_CLINICOS'] - newKeys['QTD_ACU_OUTROS_CLINICOS']
    newKeys['QT_ACU_USO_OUTROS_CIRURGICO'] = newKeys['QT_SUS_OUTROS_CIRURGIA'] - newKeys['QTD_ACU_OUTROS_CIRURGIA']

    newKeys = newKeys.apply(lambda row: _logica_roubo_leito(row,['QT_SUS_CANCER_CLINICOS'],['QT_SUS_CANCER_CIRURGIA']),axis=1)

    hospDfSoCancer = newKeys[['DATA','CNES','QT_SUS_DYN_CANCER_CLINICO','QT_SUS_DYN_CANCER_CIRURGICO','QTD_RELEASE_CANCER_CLINICOS','QTD_RELEASE_CANCER_CIRURGIA','QTD_ACU_CANCER_CLINICOS','QTD_ACU_CANCER_CIRURGIA']]

    hospDfSoCancer1 = pd.melt(hospDfSoCancer,id_vars=['DATA','CNES'],value_vars=['QT_SUS_DYN_CANCER_CLINICO','QT_SUS_DYN_CANCER_CIRURGICO'],value_name='QT_SUS',var_name='TP_PAC_AGRP')
    hospDfSoCancer1['TP_PAC_AGRP'] = hospDfSoCancer1['TP_PAC_AGRP'].replace('QT_SUS_DYN_CANCER_CLINICO','CLINICO')
    hospDfSoCancer1['TP_PAC_AGRP'] = hospDfSoCancer1['TP_PAC_AGRP'].replace('QT_SUS_DYN_CANCER_CIRURGICO','CIRURGICO')

    hospDfSoCancer2 = pd.melt(hospDfSoCancer,id_vars=['DATA','CNES'],value_vars=['QTD_RELEASE_CANCER_CLINICOS','QTD_RELEASE_CANCER_CIRURGIA'],value_name='QTD_RELEASE',var_name='TP_PAC_AGRP')
    hospDfSoCancer2['TP_PAC_AGRP'] = hospDfSoCancer2['TP_PAC_AGRP'].replace('QTD_RELEASE_CANCER_CLINICOS','CLINICO')
    hospDfSoCancer2['TP_PAC_AGRP'] = hospDfSoCancer2['TP_PAC_AGRP'].replace('QTD_RELEASE_CANCER_CIRURGIA','CIRURGICO')

    hospDfSoCancer3 = pd.melt(hospDfSoCancer,id_vars=['DATA','CNES'],value_vars=['QTD_ACU_CANCER_CLINICOS','QTD_ACU_CANCER_CIRURGIA'],value_name='QTD_ACU',var_name='TP_PAC_AGRP')
    hospDfSoCancer3['TP_PAC_AGRP'] = hospDfSoCancer3['TP_PAC_AGRP'].replace('QTD_ACU_CANCER_CLINICOS','CLINICO')
    hospDfSoCancer3['TP_PAC_AGRP'] = hospDfSoCancer3['TP_PAC_AGRP'].replace('QTD_ACU_CANCER_CIRURGIA','CIRURGICO')

    hospDfSoCancer = hospDfSoCancer1.merge(hospDfSoCancer2, how='inner', on=['DATA','CNES','TP_PAC_AGRP'])    
    hospDfSoCancer = hospDfSoCancer.merge(hospDfSoCancer3, how='inner', on=['DATA','CNES','TP_PAC_AGRP'])

    hospDfSoCancer['TP_PAC_AGRP'] = hospDfSoCancer['TP_PAC_AGRP'].replace('CLINICO',codCancerCli)
    hospDfSoCancer['TP_PAC_AGRP'] = hospDfSoCancer['TP_PAC_AGRP'].replace('CIRURGICO',codCancerCir)
    hospDfSoCancer['TP_PAC_AGRP'] = hospDfSoCancer['TP_PAC_AGRP'].astype(int)

    dfSanidade = newKeys[['DATA','CNES','QT_ACU_CANCER_TT_REAL','QT_ACU_OUTROS_TT_REAL','QT_SUS_DYN_CANCER_CLINICO','QT_SUS_DYN_CANCER_CIRURGICO']]

    hospDfSoCancer = hospDfSoCancer.astype(int)
    dfSanidade = dfSanidade.astype(int)

    dfSanidade.to_csv('debugRouboLeito.csv',index=False)

    #df/dic com quantidade inicial de pacientes cnes/tipo
    dfCumSum = hospDfSoCancer[['DATA','CNES','TP_PAC_AGRP','QTD_RELEASE']]
    dfCumSum = dfCumSum.sort_values(by=['DATA','CNES','TP_PAC_AGRP'])
    dfCumSum['QTD_RELEASE_SUM'] = dfCumSum.groupby(['CNES','TP_PAC_AGRP'])['QTD_RELEASE'].cumsum()
    dfCumSum.set_index(['DATA','CNES','TP_PAC_AGRP'],inplace=True)
    dfCumSum  = {index:row['QTD_RELEASE_SUM'] for index, row in dfCumSum.iterrows()} 

    dfInitFix = hospDfSoCancer[['CNES','TP_PAC_AGRP','QTD_ACU']][hospDfSoCancer['DATA']==min(hospDfSoCancer['DATA'])].drop_duplicates()
    dfInitFix.set_index(['CNES','TP_PAC_AGRP'],inplace=True)
    dfInitFix  = {index:row['QTD_ACU'] for index, row in dfInitFix.iterrows()} 

    hospDfSoCancer = hospDfSoCancer.apply(lambda row: _logica_fix_init(row,dfInitFix,dfCumSum),axis=1)

    hospDfSoCancer = hospDfSoCancer[hospDfSoCancer['QT_SUS']>0]

    return hospDfSoCancer

def encoding_patType(patDf:pd.DataFrame,hospDf:pd.DataFrame,dfDemandaCancer:pd.DataFrame):

    toEnc = np.expand_dims(np.unique(patDf['TP_PAC_AGRP']),axis=0).T
    toEncInd = np.expand_dims(np.arange(toEnc.shape[0]),axis=0).T

    encNp = np.concatenate((toEnc,toEncInd),axis=1)

    encdF = pd.DataFrame(encNp,columns=['TP_PAC_AGRP','IDX'])

    patDf = patDf.merge(encdF,on='TP_PAC_AGRP')
    hospDf = hospDf.merge(encdF,on='TP_PAC_AGRP')
    dfDemandaCancer = dfDemandaCancer.merge(encdF,on='TP_PAC_AGRP')

    patDf.drop(columns=['TP_PAC_AGRP'],inplace=True)
    hospDf.drop(columns=['TP_PAC_AGRP'],inplace=True)
    dfDemandaCancer.drop(columns=['TP_PAC_AGRP'],inplace=True)

    patDf.rename(columns={'IDX':'TP_PAC_AGRP'},inplace=True)
    hospDf.rename(columns={'IDX':'TP_PAC_AGRP'},inplace=True)
    dfDemandaCancer.rename(columns={'IDX':'TP_PAC_AGRP'},inplace=True)

    #organizing columns sequence:
    patDf = patDf[['DT_INTER','MUNIC_RES','TP_PAC_AGRP','QTY','MED_PERM']]
    hospDf = hospDf[['DATA','CNES','TP_PAC_AGRP','QTD_POS','QTD_NEG','QTD_NET','QTD_ACU','QTD_RELEASE','QT_SUS']]
    dfDemandaCancer = dfDemandaCancer[['DT_INTER','MUNIC_RES','TP_PAC_AGRP','QTY']]

    return patDf,hospDf,dfDemandaCancer,encdF

def _deparaLeitos(row):

    if row['CO_LEITO'] in [12]:
        row['DESC_LEITO'] = 'CANCER_CIRURGIA'
    elif row['CO_LEITO'] in [44]:
        row['DESC_LEITO'] = 'CANCER_CLINICOS'
    elif row['TP_LEITO'] in [1]:
        row['DESC_LEITO'] = 'OUTROS_CIRURGIA'
    else:
        row['DESC_LEITO'] = 'OUTROS_CLINICOS'

    return row

def _deparaAgrupDoenca(row):

    if row['Chapter_Desc'] == 'Neoplasms (C00-D48)':
        row['TP_DOENCA_AGRUPADA'] = 'CANCER'
    else:
        row['TP_DOENCA_AGRUPADA'] = 'OUTROS'

    return row

def _deparaCancer(row):

    if row['Chapter_Desc'] == 'Neoplasms (C00-D48)':
        row['TP_DOENCA'] = 'CANCER'
    elif row['ICD_10'] == 'B342':
        row['TP_DOENCA'] = 'COVID'
    else:
        row['TP_DOENCA'] = 'OUTROS'

    return row

def _deparaProc(row):

    if row['Nome_Grupo_1'] == 'Procedimentos cirúrgicos':
        row['TP_PROC'] = 'CIRURGIA'
    else:
        row['TP_PROC'] = 'CLINICOS'

    return row

def _load_deparas(dffPaciente:pd.DataFrame,dfdLeiPath:pd.DataFrame, dffProfission:pd.DataFrame):

    #curDir = os.path.dirname(os.path.realpath(__file__))
    curDir = os.path.abspath(os.path.join(os.path.dirname( __file__ ), '..'))

    cboPath = os.path.join(curDir,'data','external','deParaCBO.csv')
    cidPath = os.path.join(curDir,'data','external','deParaCID.csv')
    cnesPath = os.path.join(curDir,'data','external','deparaCnes.csv')
    gLeitoPath = os.path.join(curDir,'data','external','deParaGLeito.csv')
    leitoEspecPath = os.path.join(curDir,'data','external','deParaLeitoEspec.csv')
    leitosPath = os.path.join(curDir,'data','external','deParaLeitos.csv')
    procPath = os.path.join(curDir,'data','external','deparaProcedimentos.csv')
    tipoEstabPath = os.path.join(curDir,'data','external','deParaTipoEsb.csv')
    cboPath = os.path.join(curDir,'data','external','deParaCBO.csv')

    cboDf = pd.read_csv(cboPath,sep=",",encoding="latin")
    cidDf = pd.read_csv(cidPath,sep=",",encoding="latin")
    cnesDf = pd.read_csv(cnesPath,sep=",",encoding="latin")
    gLeitoDf = pd.read_csv(gLeitoPath,sep=",",encoding="latin")
    leitoEsPDf = pd.read_csv(leitoEspecPath,sep=",",encoding="latin")
    leitosDf = pd.read_csv(leitosPath,sep=",",encoding="latin")
    procDf = pd.read_csv(procPath,sep=",",encoding="latin")
    tpEstabDf = pd.read_csv(tipoEstabPath,sep=",",encoding="latin")
    cboDf = pd.read_csv(cboPath,sep=",",encoding="latin")

    cidDf = cidDf.apply(lambda row: _deparaCancer(row),axis=1)
    cidDf = cidDf.apply(lambda row: _deparaAgrupDoenca(row),axis=1)
    procDf = procDf.apply(lambda row: _deparaProc(row),axis=1)
    leitosDf = leitosDf.apply(lambda row: _deparaLeitos(row),axis=1)

    dffProfission = dffProfission.merge(cboDf,how='left',left_on='CBO',right_on='cod_cbo')
    dffProfission['Nome_Cbo'].fillna("Outros",inplace=True)

    dffProfission['HORAS'] = (dffProfission['HORA_AMB'] + dffProfission['HORAHOSP'] + dffProfission['HORAOUTR']) / 5
    dffProfission['HORAS'] = dffProfission['HORAS'].astype(int)
    dffProfission.drop(columns=['HORA_AMB','HORAHOSP','HORAOUTR'],inplace=True)

    dffProfission = dffProfission.groupby(by=['CNES','Nome_Cbo','COMPETEN','HORAS']).agg({'CBO':'count'}).reset_index()

    dffPaciente = dffPaciente.merge(cidDf[['ICD_10','TP_DOENCA','TP_DOENCA_AGRUPADA']], how='left', left_on='DIAG_PRINC',right_on='ICD_10')
    dffPaciente = dffPaciente.merge(procDf[['Codigo','TP_PROC']], how='left', left_on='PROC_REA',right_on='Codigo')
    dfdLeiPath = dfdLeiPath.merge(leitosDf[['CO_LEITO','DESC_LEITO']], how='left', left_on='CODLEITO',right_on='CO_LEITO')

    dffPaciente['TP_DOENCA'].fillna("OUTROS",inplace=True)
    dffPaciente['TP_DOENCA_AGRUPADA'].fillna("OUTROS",inplace=True)
    dffPaciente['TP_PROC'].fillna("CLINICOS",inplace=True)

    dffPaciente['TP_PAC_AGRP'] = dffPaciente['TP_DOENCA'].astype(str) + '_' + dffPaciente['TP_PROC'].astype(str)
    dffPaciente['TP_PAC_AGRP_AGRUPADA'] = dffPaciente['TP_DOENCA_AGRUPADA'].astype(str) + '_' + dffPaciente['TP_PROC'].astype(str)

    dfDemandaCancer = dffPaciente[(dffPaciente['DT_INTER']>=20190101) & (dffPaciente['DT_INTER']<20200232)]
    dfDemandaCancer = dfDemandaCancer[(dfDemandaCancer['TP_PAC_AGRP']=='CANCER_CIRURGIA') | (dfDemandaCancer['TP_PAC_AGRP']=='CANCER_CLINICOS')]

    dfDemandaCancer = dfDemandaCancer.groupby(by=['DT_INTER','MUNIC_RES','TP_PAC_AGRP']).agg({'N_AIH':'count'}).reset_index()
    dfDemandaCancer.rename(columns={'N_AIH':'QTY'},inplace=True)
    dfDemandaCancer['Timestamp'] = pd.to_datetime(dfDemandaCancer['DT_INTER'], format='%Y%m%d')

    return dffPaciente, dfdLeiPath, dfDemandaCancer, dffProfission