FROM python:3.11-slim

WORKDIR /notebooks

RUN pip install --no-cache-dir \
    jupyterlab>=4.0 \
    neo4j>=5.18.0 \
    redis[hiredis]>=5.0.0 \
    httpx>=0.27.0 \
    numpy>=1.26.0 \
    pandas>=2.2.0 \
    networkx>=3.2.0 \
    matplotlib>=3.8.0

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=kglab"]
