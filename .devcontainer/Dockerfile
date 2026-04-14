FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ARG DEBIAN_FRONTEND=noninteractive

# --------------------------------------------------------
# Install ALL system + Qt deps (ROOT)
# --------------------------------------------------------
USER root

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    pkg-config \
    python3 \
    python3-pip \
    libzmq3-dev \
    libsqlite3-dev \
    graphviz \
    nlohmann-json3-dev \
    libtinyxml2-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

USER vscode
WORKDIR /workspace

RUN git clone --depth 1 https://github.com/BehaviorTree/BehaviorTree.CPP.git /workspace/BehaviorTree.CPP && \
    cmake -S /workspace/BehaviorTree.CPP -B /workspace/BehaviorTree.CPP/build \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_TESTING=OFF && \
    cmake --build /workspace/BehaviorTree.CPP/build -j