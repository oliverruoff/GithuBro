FROM node:22-bookworm-slim AS node
FROM python:3.12-slim
COPY --from=node /usr/local /usr/local
RUN apt-get update && apt-get install -y --no-install-recommends bash ca-certificates cron curl git openssh-client tree tzdata \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg -o /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*
ARG CACHEBUST=unset
RUN npm install -g @earendil-works/pi-coding-agent@latest
WORKDIR /opt/githubro
COPY app/requirements.txt /opt/githubro/app/requirements.txt
RUN pip install --no-cache-dir -r /opt/githubro/app/requirements.txt
COPY app/ /opt/githubro/app/
COPY extensions/package.json extensions/package-lock.json /root/.pi/agent/
RUN cd /root/.pi/agent && npm install --omit=dev --ignore-scripts
COPY extensions/src/ /root/.pi/agent/extensions/
COPY AGENTS.md /root/.pi/agent/AGENTS.md
COPY skills/ /workspace/skills/
RUN mkdir -p /root/.pi/agent /workspace/skills && ln -s /workspace/skills /root/.pi/agent/skills
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/opt/githubro
CMD ["python", "-m", "app"]
