FROM python:3.11-slim

# Install system dependencies, Git, Node.js, GitHub CLI, and bash-completion
RUN apt-get update && apt-get install -y \
    curl \
    git \
    bash \
    bash-completion \
    jq \
    build-essential \
    nano \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
    && apt-get update && apt-get install -y gh \
    && rm -rf /var/lib/apt/lists/*

# Enable bash tab-completion for all shells (interactive and non-interactive)
RUN echo '. /usr/share/bash-completion/bash_completion' >> /etc/bash.bashrc

# Enable a color prompt and colorized ls/grep for root (Debian slim ships no
# /root/.bashrc, so none of this exists by default for the root user)
RUN { \
    echo 'force_color_prompt=yes'; \
    echo 'PS1="\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ "'; \
    echo 'export TERM=xterm-256color'; \
    echo 'export CLICOLOR=1'; \
    echo "alias ls='ls --color=auto'"; \
    echo "alias grep='grep --color=auto'"; \
    echo 'test -r /usr/share/bash-completion/bash_completion && . /usr/share/bash-completion/bash_completion'; \
    } >> /root/.bashrc

# Install global NPM packages for tools like Claude Code or standard linters
RUN npm install -g @anthropic-ai/claude-code @fresh-editor/fresh-editor

# Default editor for git, gh, etc.
ENV EDITOR=nano

# Establish working environments
WORKDIR /workspace

# Default entry point
CMD ["/bin/bash"]
