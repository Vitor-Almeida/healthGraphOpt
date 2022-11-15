def testing(CONCapacityrht,InitPatientsph,releasePatientspht,initialTime,xContinuidade,split):

    #check if all initpat are in capacity

    newXDic = {}
    newReleaseDic = {}
    for key in releasePatientspht:
        newReleaseDic[key[0],key[1]] = 0

    for key in releasePatientspht:
        newReleaseDic[key[0],key[1]] += releasePatientspht[key]
    
    cidadesCapac=[]
    for key in CONCapacityrht:
        cidadesCapac.append(key[1])

        if key[2] == initialTime:
            check = (InitPatientsph.get((key[0],key[1]),0) + newReleaseDic.get((key[0],key[1]),0)) > CONCapacityrht[key[0],key[1],initialTime]
            if check:
                print('ERROR: ',key[0],key[1],' com capacidade menor que qtd inicial')

    for key in InitPatientsph:
        check = newReleaseDic.get((key[0],key[1]),0) > InitPatientsph.get((key[0],key[1]),0)
        if check:
            print('ERROR: ',key[0],key[1],' quantidade de saída maior que pacientes inciais')


    #if split>0:
    #
    #    for key in xContinuidade:
    #        newXDic[key[0],key[2]] = 0
    #
    #    for key in xContinuidade:
    #        newXDic[key[0],key[2]] += xContinuidade[key]
    #
    #    for key in CONCapacityrht:
    ##        if key[2] == initialTime:
    #           check = (newXDic.get((key[0],key[1]),0) + newReleaseDic.get((key[0],key[1]),0)) > CONCapacityrht[key[0],key[1],initialTime]
    #            if check:
    #                print('ERROR: ',key[0],key[1],' com capacidade menor que qtd inicial')


    #checar dias faltando:


    return None


