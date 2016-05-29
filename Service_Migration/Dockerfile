FROM hypriot/rpi-python

RUN pip install docker-py redis
RUN mkdir proxy

COPY dockerctl.py proxyserver.py redisdb.py /proxy/

WORKDIR /proxy

CMD python proxyserver.py
