import os
import pandas as pd
import numpy as np

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

        columnsRepetirNan = columnsRepetirNan + ['QTD_ACU'+str(encdF.iloc[types,0]), 'QT_SUS'+str(encdF.iloc[types,0])]


    for df in dfVector:
        newKeys = newKeys.join(df)

    newKeys.reset_index(inplace=True)

    for cols in newKeys.columns:
        if cols in columnsZerarNan:
            newKeys[cols].fillna(0,inplace=True)
        else:
            newKeys[cols].fillna(method='ffill',inplace=True)
            newKeys[cols].fillna(0,inplace=True)

    qtdAcuCovidTT = list(filter(lambda x: 'QTD_ACU' in x and 'COVID' in x, newKeys.columns))
    qtdAcuCancerTT = list(filter(lambda x: 'QTD_ACU' in x and 'CANCER' in x, newKeys.columns))
    qtdAcuOutrosTT = list(filter(lambda x: 'QTD_ACU' in x and 'CANCER' not in x, newKeys.columns))

    qtdAcuClin = list(filter(lambda x: 'QTD_ACU' in x and 'CLINICOS' in x and 'CANCER' not in x, newKeys.columns))
    qtdAcuCir = list(filter(lambda x: 'QTD_ACU' in x and 'CIRURGIA' in x and 'CANCER' not in x, newKeys.columns))
    qtdSusClin = list(filter(lambda x: 'QT_SUS' in x and 'CLINICOS' in x and 'CANCER' not in x, newKeys.columns))
    qtdSusCir = list(filter(lambda x: 'QT_SUS' in x and 'CIRURGIA' in x and 'CANCER' not in x, newKeys.columns))

    #qtdAcuClinC = list(filter(lambda x: 'QTD_ACU' in x and 'CLINICOS' in x and 'CANCER' in x, newKeys.columns))
    #qtdAcuCirC = list(filter(lambda x: 'QTD_ACU' in x and 'CIRURGIA' in x and 'CANCER' in x, newKeys.columns))
    qtdSusClinC = list(filter(lambda x: 'QT_SUS' in x and 'CLINICOS' in x and 'CANCER' in x, newKeys.columns))
    qtdSusCirC = list(filter(lambda x: 'QT_SUS' in x and 'CIRURGIA' in x and 'CANCER' in x, newKeys.columns))

    newKeys['QT_ACU_COVID_TT_REAL'] =  newKeys[qtdAcuCovidTT].sum(axis=1)
    newKeys['QT_ACU_CANCER_TT_REAL'] =  newKeys[qtdAcuCancerTT].sum(axis=1)
    newKeys['QT_ACU_OUTROS_TT_REAL'] =  newKeys[qtdAcuOutrosTT].sum(axis=1)

    newKeys['QT_SUS_DYN_CANCER_CLINICO'] = newKeys[qtdSusClinC].sum(axis=1)
    newKeys['QT_SUS_DYN_CANCER_CIRURGICO'] = newKeys[qtdSusCirC].sum(axis=1)

    newKeys['QT_ACU_USO_OUTROS_CLINICO'] = newKeys[qtdSusClin].sum(axis=1) - newKeys[qtdAcuClin].sum(axis=1)
    newKeys['QT_ACU_USO_OUTROS_CIRURGICO'] = newKeys[qtdSusCir].sum(axis=1) - newKeys[qtdAcuCir].sum(axis=1)

    newKeys = newKeys.apply(lambda row: _logica_roubo_leito(row,qtdSusClinC,qtdSusCirC),axis=1)

    hospDfSoCancer = newKeys[['DATA','CNES','QT_SUS_DYN_CANCER_CLINICO','QT_SUS_DYN_CANCER_CIRURGICO']]
    hospDfSoCancer = pd.melt(hospDfSoCancer,id_vars=['DATA','CNES'],value_vars=['QT_SUS_DYN_CANCER_CLINICO','QT_SUS_DYN_CANCER_CIRURGICO'],value_name='QT_SUS',var_name='TP_PAC_AGRP')
    hospDfSoCancer['TP_PAC_AGRP'] = hospDfSoCancer['TP_PAC_AGRP'].replace('QT_SUS_DYN_CANCER_CLINICO',codCancerCli)
    hospDfSoCancer['TP_PAC_AGRP'] = hospDfSoCancer['TP_PAC_AGRP'].replace('QT_SUS_DYN_CANCER_CIRURGICO',codCancerCir)
    hospDfSoCancer['TP_PAC_AGRP'] = hospDfSoCancer['TP_PAC_AGRP'].astype(int)

    patDfCovidAcu = newKeys[['DATA','CNES','QT_ACU_COVID_TT_REAL']]
    patDfCovidAcu.rename(columns={'QT_ACU_COVID_TT_REAL':'QTD_ACU'},inplace=True)
    dfSanidade = newKeys[['DATA','CNES','QT_ACU_COVID_TT_REAL','QT_ACU_CANCER_TT_REAL','QT_ACU_OUTROS_TT_REAL','QT_SUS_DYN_CANCER_CLINICO','QT_SUS_DYN_CANCER_CIRURGICO']]

    hospDfSoCancer = hospDfSoCancer.astype(int)
    patDfCovidAcu = patDfCovidAcu.astype(int)
    dfSanidade = dfSanidade.astype(int)

    dfSanidade.to_csv('debugRouboLeito.csv',index=False)

    return hospDfSoCancer, patDfCovidAcu

def encoding_patType(patDf:pd.DataFrame,hospDf:pd.DataFrame):

    toEnc = np.expand_dims(np.unique(patDf['TP_PAC_AGRP']),axis=0).T
    toEncInd = np.expand_dims(np.arange(toEnc.shape[0]),axis=0).T

    encNp = np.concatenate((toEnc,toEncInd),axis=1)

    encdF = pd.DataFrame(encNp,columns=['TP_PAC_AGRP','IDX'])

    patDf = patDf.merge(encdF,on='TP_PAC_AGRP')
    hospDf = hospDf.merge(encdF,on='TP_PAC_AGRP')
    patDf.drop(columns=['TP_PAC_AGRP'],inplace=True)
    hospDf.drop(columns=['TP_PAC_AGRP'],inplace=True)

    patDf.rename(columns={'IDX':'TP_PAC_AGRP'},inplace=True)
    hospDf.rename(columns={'IDX':'TP_PAC_AGRP'},inplace=True)

    #organizing columns sequence:
    patDf = patDf[['DT_INTER','MUNIC_RES','TP_PAC_AGRP','QTY','MED_PERM']]
    hospDf = hospDf[['DATA','CNES','TP_PAC_AGRP','QTD_POS','QTD_NEG','QTD_NET','QTD_ACU','QTD_RELEASE','QT_SUS']]

    return patDf,hospDf,encdF


def _deparaLeitos(row):

    if row['CO_LEITO'] in [12]:
        row['DESC_LEITO'] = 'CANCER_CIRURGIA'
    elif row['CO_LEITO'] in [44]:
        row['DESC_LEITO'] = 'CANCER_CLINICOS'
    elif row['CO_LEITO'] in [96]:
        row['DESC_LEITO'] = 'COVID_CLINICOS'
    elif row['TP_LEITO'] in [1]:
        row['DESC_LEITO'] = 'OUTROS_CIRURGIA'
    else:
        row['DESC_LEITO'] = 'OUTROS_CLINICOS'

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

def _load_deparas(dffPaciente:pd.DataFrame,dfdLeiPath:pd.DataFrame):

    curDir = os.path.dirname(os.path.realpath(__file__))

    cboPath = os.path.join(curDir,'data','external','deParaCBO.csv')
    cidPath = os.path.join(curDir,'data','external','deParaCID.csv')
    cnesPath = os.path.join(curDir,'data','external','deparaCnes.csv')
    gLeitoPath = os.path.join(curDir,'data','external','deParaGLeito.csv')
    leitoEspecPath = os.path.join(curDir,'data','external','deParaLeitoEspec.csv')
    leitosPath = os.path.join(curDir,'data','external','deParaLeitos.csv')
    procPath = os.path.join(curDir,'data','external','deparaProcedimentos.csv')
    tipoEstabPath = os.path.join(curDir,'data','external','deParaTipoEsb.csv')

    cboDf = pd.read_csv(cboPath,sep=",",encoding="latin")
    cidDf = pd.read_csv(cidPath,sep=",",encoding="latin")
    cnesDf = pd.read_csv(cnesPath,sep=",",encoding="latin")
    gLeitoDf = pd.read_csv(gLeitoPath,sep=",",encoding="latin")
    leitoEsPDf = pd.read_csv(leitoEspecPath,sep=",",encoding="latin")
    leitosDf = pd.read_csv(leitosPath,sep=",",encoding="latin")
    procDf = pd.read_csv(procPath,sep=",",encoding="latin")
    tpEstabDf = pd.read_csv(tipoEstabPath,sep=",",encoding="latin")

    cidDf = cidDf.apply(lambda row: _deparaCancer(row),axis=1)
    procDf = procDf.apply(lambda row: _deparaProc(row),axis=1)
    leitosDf = leitosDf.apply(lambda row: _deparaLeitos(row),axis=1)

    dffPaciente = dffPaciente.merge(cidDf[['ICD_10','TP_DOENCA']], left_on='DIAG_PRINC',right_on='ICD_10')
    dffPaciente = dffPaciente.merge(procDf[['Codigo','TP_PROC']], left_on='PROC_REA',right_on='Codigo')
    dfdLeiPath = dfdLeiPath.merge(leitosDf[['CO_LEITO','DESC_LEITO']], left_on='CODLEITO',right_on='CO_LEITO')

    dffPaciente['TP_PAC_AGRP'] = dffPaciente['TP_DOENCA'].astype(str) + '_' + dffPaciente['TP_PROC'].astype(str)

    return dffPaciente, dfdLeiPath