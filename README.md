# healthGraphOpt
allocation optimization of pacients during a pandemic using real data from Brazil 2020-2022 period

#instalar pyomo
pip install pyomo

#instalar glpk
sudo apt-get install -y -qq glpk-utils

#instalar coin-or cbc
sudo apt-get install -y -qq coinor-cbc

#instalar coin-or ipopt installation
wget -N -q "https://ampl.com/dl/open/ipopt/ipopt-linux64.zip"
sudo unzip -o -q ipopt-linux64

#COIN-OR Bonmin installation
wget -N -q "https://ampl.com/dl/open/bonmin/bonmin-linux64.zip"
unzip -o -q bonmin-linux64

#COIN-OR Couenne installation
wget -N -q "https://ampl.com/dl/open/couenne/couenne-linux64.zip"
unzip -o -q couenne-linux64
#Gecode installation
wget -N -q "https://ampl.com/dl/open/gecode/gecode-linux64.zip"
unzip -o -q gecode-linux64