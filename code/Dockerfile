FROM jupyter/datascience-notebook:latest

USER ${NB_UID}

RUN pip install dbfread
RUN pip install linearmodels
RUN pip install geopandas


USER root
RUN sudo apt-get update
RUN sudo apt-get install -y tesseract-ocr
RUN pip install pytesseract
RUN pip install google-cloud-bigquery pandas-gbq google-cloud-storage pyarrow
RUN pip install gcsfs tqdm polars
RUN pip install bigframes
RUN pip install pyreadstat
RUN pip install pyblp pdfplumber rapidfuzz networkx
# Issue #3: staggered DiD stack. R is the reference implementation for Callaway-Sant'Anna (did),
# Sun-Abraham (fixest::sunab) and HonestDiD; pyfixest gives a Python cross-check.
RUN pip install pyfixest
RUN Rscript -e 'install.packages(c("did","fixest","didimputation","bacondecomp","remotes"), repos="https://cloud.r-project.org")'
# HonestDiD is not on CRAN; Rglpk only builds against conda's glpk (system libglpk is not picked up)
RUN mamba install -y -q -c conda-forge glpk
# CVXR >=1.1 needs a Rust toolchain (clarabel); pin the last pre-Rust release
RUN Rscript -e 'remotes::install_version("CVXR","1.0-15",repos="https://cloud.r-project.org"); install.packages(c("Rglpk","matrixStats","latex2exp","lpSolveAPI","pracma","mvtnorm","TruncatedNormal"),repos="https://cloud.r-project.org"); remotes::install_github("asheshrambachan/HonestDiD", dependencies=FALSE); stopifnot(requireNamespace("HonestDiD"))'

RUN mkdir /home/repo-intro
RUN cd /home/repo-intro
WORKDIR /home/repo-intro

RUN mkdir /home/repo-intro/build
RUN mkdir /home/repo-intro/analysis

ENV NOTEBOOK_ARGS="--NotebookApp.token='' --NotebookApp.password=''"
COPY requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 8888