from healthgraphopt.optimization import run_simulation
from dataloader.load_data import load_data

def main():

    initialTime=20210401
    durationTime=4

    dataDic = load_data(initialTime,durationTime)

    run_simulation(initialTime,dataDic)

if __name__ == '__main__':
    main()