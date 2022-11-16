<a name="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <a href="https://github.com/Vitor-Almeida/healthGraphOpt">
    <img src="docs/logo.png" alt="Logo" width="80" height="80">
  </a>

<h3 align="center">Optimal Allocation of Cancer patients during a pandemic</h3>

  <p align="center">
  More than 50% of all Cancer patients were unable to receive care during the SARS-CoV-2 pandemic [1]. Due to crowded hospitals, high risk of contamination or long travelling distances. This project aims to optimally find the best allocation of these patients by minimizing travelled distance and contamination risk. The problem is modeled using <b>integer linear programming</b> and a <b>multi-objective function</b> using the weighted method.
    <br />
    <a href="https://github.com/Vitor-Almeida/healthGraphOpt/issues">Report Bug</a>
    ·
    <a href="https://app.powerbi.com/view?r=eyJrIjoiMWY4ZWZjYTUtODgxNi00ZDYzLWFkMDQtY2MyZDg3ZmJiOWI2IiwidCI6IjJiM2NjNTIzLWFmMzItNDU5Mi1hN2VhLWZkNTRlMmRkNTU3ZCJ9">Power BI Dashboard</a>
    ·
    <a href="https://github.com/Vitor-Almeida/healthGraphOpt/issues">Request Feature</a>
  </p>
</div>

<!-- ABOUT THE PROJECT -->
## About The Data

<!-- Colocar uma imagem de grafo aqui:
[![Product Name Screen Shot][product-screenshot]](https://app.powerbi.com/view?r=eyJrIjoiMWY4ZWZjYTUtODgxNi00ZDYzLWFkMDQtY2MyZDg3ZmJiOWI2IiwidCI6IjJiM2NjNTIzLWFmMzItNDU5Mi1hN2VhLWZkNTRlMmRkNTU3ZCJ9)
-->

This project uses real data from [DataSUS](https://datasus.saude.gov.br/). It contains all medical procedures performed by doctors in Brazil's public health system. The database granularity goes all the way to the Patient level.

The following informations were used from the Database:
* Local of origin of the patient.
* Which health unit the procedure was realized.
* Patient medical diagnostic .
* Which medical procedure was performed (surgical, clinical etc.).
* Day of the patient hospitalization and day of discharge.

The database also has information about all the country's health units. 

* Number of available beds
* Number of equipment and type of equipment
* Number of doctors and its specializations.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Built With
* [![Python.py][Python.py]][Python-url]
* [![Pandas.py][Pandas.py]][Pandas-url]
* [![Numpy.py][Numpy.py]][Numpy-url]
* [![PowerBI][PowerBI]][PowerBI-url]
* [https://github.com/Pyomo/pyomo](https://github.com/Pyomo/pyomo)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- GETTING STARTED -->
## The problem

[![Product Name Screen Shot][product-screenshot]](https://app.powerbi.com/view?r=eyJrIjoiMWY4ZWZjYTUtODgxNi00ZDYzLWFkMDQtY2MyZDg3ZmJiOWI2IiwidCI6IjJiM2NjNTIzLWFmMzItNDU5Mi1hN2VhLWZkNTRlMmRkNTU3ZCJ9)

During the first and second wave of Covid, we can cleary see a decline in Cancer patients admissions. -48% we comparing the same period vs LY.

fix:
We can also see a node concentration of countryside patients to only wanting to get treatment at the capital.1

## The model

### Variables
  ```sh
  SETS:
  * H->	hospitals
  * A->	population areas (demand points)
  * T->	periods in the current planning horizon
  * R-> type of bed
  * P-> patient type
  * Sr-> Set of patient type requiring bed type R
  ```

  ```sh
  PARAMETERS
  * ar-> attack rate (fixed)
  * Distance(ah)-> distance from population area a to hospital h
  * Demand(pat)-> demand of patient type p from area a on day t
  * CONCapacity(rh)-> initial capacity of resource r in hospital h
  * LOS(p)-> length of stay (i.e. how many days) for patient type p
  * InitPatients(ph)-> number of patient type p at hospital h prior to the planning horizon
  * ReleasedPatients(pht)-> number of patient type p at hospital h prior to the planning horizon who are released on day t
  * StaffHrs(p)-> average number of hours per day that a medical staff attends to a patient of type p
  * StaffCap(h,t)-> number of available hours per day of all medical staff on day t at hospital h
  ```

  ```sh
  INTERMEDIATE VARIABLES:
  NoPatients(pht)-> number of patient type p at hospital h on day t
  NoCovidPatients(ht)-> number of covid patients at hospital h on day t
  DECISION VARIABLE:
  X(paht)-> number of patient type p from area a assigned to hospital h on day t
  ```

### Objective Function

**Minimization of the total travel distance between patients and healthcare facilities**
$$Min \sum_p\sum_a\sum_h\sum_tX_{paht} \ast Distance_{ah}$$

**Minimization of infection risk**
$$Min \sum_t\sum_h( \sum_p\sum_aX_{paht} + NoCovidPatients_{th}) \ast ar$$

### Constrains

$$\sum_hX_{paht} = Demand_{pat}$$

$$NoPatients_{ph1} = InitPatients_{ph} + \sum_aX_{pah1}$$

$$NoPatients_{pht} = NoPatients_{pht-1} + \sum_aX_{paht} - \sum_aX_{pah(t-LOS_{p})} - ReleasedPatients{pht}$$

$$\sum_{p\in S_{r}}NoPatients_{pht} \leqslant CONCapacity_{rh}$$

$$\sum_{p}(NoPatients_{pht}\ast StaffHrs_{p}) \leqslant StaffCap_{ht}$$

$$X_{paht} \geqslant 0 \hspace{1cm} \forall p,a,h,t$$

### Results

1. G
2. C
   ```sh
   1
   ```
3. I
   ```sh
   1
   ```
4. E
   ```js
   1
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTRIBUTING -->
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- REFERENCES -->
## References

1. [Adam F. Abdin, Y.-P. F. (2021). An optimization model for planning testing and control strategies to limit the spread of a pandemic – The case of COVID-19. European Journal of Operational Research, 308-324.](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8614228/)

2. [Li Sun, G. W. (2014). Multi-objective optimization models for patient allocation during a pandemic influenza outbreak. Computers & Operations Research, 350-359.](https://www.sciencedirect.com/science/article/abs/pii/S0305054813003468)

3. [M. Bonsignore, S. H. (2022). Burden of hospital-acquired SARS-CoV-2 infections in Germany: occurrence and outcomes of different variants. Journal of Hospital Infection , 82-88.](https://www.sciencedirect.com/science/article/pii/S0195670122002584)

4. [Nezir Aydin, Z. C. (2022). Analyses on ICU and non-ICU capacity of government hospitals during the COVID-19 outbreak via multi-objective linear programming: An evidence from Istanbul. Computers in Biology and Medicine , 1-22.](https://pubmed.ncbi.nlm.nih.gov/35569338/)

5. [Osama M. Al-Quteimat, A. M. (2020). The Impact of the COVID-19 Pandemic on Cancer Patients. American Journal of Clinical Oncology.](https://pubmed.ncbi.nlm.nih.gov/32304435/)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- CONTACT -->
## Contact

Vitor Freitas de Almeida - [linkedin](https://www.linkedin.com/in/vitorfalmeida/) - almeida.f.vitor@gmail.com

Project Link: [https://github.com/Vitor-Almeida/healthGraphOpt](https://github.com/Vitor-Almeida/healthGraphOpt)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/Vitor-Almeida/healthGraphOpt.svg?style=for-the-badge
[contributors-url]: https://github.com/Vitor-Almeida/healthGraphOpt/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/Vitor-Almeida/healthGraphOpt.svg?style=for-the-badge
[forks-url]: https://github.com/Vitor-Almeida/healthGraphOpt/network/members
[stars-shield]: https://img.shields.io/github/stars/Vitor-Almeida/healthGraphOpt.svg?style=for-the-badge
[stars-url]: https://github.com/Vitor-Almeida/healthGraphOpt/stargazers
[issues-shield]: https://img.shields.io/github/issues/Vitor-Almeida/healthGraphOpt.svg?style=for-the-badge
[issues-url]: https://github.com/Vitor-Almeida/healthGraphOpt/issues
[license-shield]: https://img.shields.io/github/license/Vitor-Almeida/healthGraphOpt.svg?style=for-the-badge
[license-url]: https://github.com/Vitor-Almeida/healthGraphOpt/blob/master/LICENSE.txt
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/vitorfalmeida
[product-screenshot]: docs/screenshot.png
[Next.js]: https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white

[Python.py]:https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[python-url]:https://www.python.org/
[Pandas.py]:https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white
[Pandas-url]:https://pandas.pydata.org/
[Numpy.py]:https://img.shields.io/badge/numpy-%23013243.svg?style=for-the-badge&logo=numpy&logoColor=white
[Numpy-url]:https://numpy.org/
[PowerBI]:https://img.shields.io/badge/power_bi-F2C811?style=for-the-badge&logo=powerbi&logoColor=black
[PowerBI-url]:https://powerbi.microsoft.com/pt-br/

[Next-url]: https://nextjs.org/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[Vue.js]: https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D
[Vue-url]: https://vuejs.org/
[Angular.io]: https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white
[Angular-url]: https://angular.io/
[Svelte.dev]: https://img.shields.io/badge/Svelte-4A4A55?style=for-the-badge&logo=svelte&logoColor=FF3E00
[Svelte-url]: https://svelte.dev/
[Laravel.com]: https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white
[Laravel-url]: https://laravel.com
[Bootstrap.com]: https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white
[Bootstrap-url]: https://getbootstrap.com
[JQuery.com]: https://img.shields.io/badge/jQuery-0769AD?style=for-the-badge&logo=jquery&logoColor=white
[JQuery-url]: https://jquery.com 
