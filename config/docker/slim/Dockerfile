# SLIM Transporter with baked-in configuration
# Base image from AGNTCY
FROM ghcr.io/agntcy/slim:0.6.1

# Copy configuration file
COPY slim.yaml /etc/slim.yaml

# Expose SLIM ports
# 46357: Primary transport port
# 46358: Secondary/health port
EXPOSE 46357 46358

# Run SLIM with the config
ENTRYPOINT ["/slim"]
CMD ["--config", "/etc/slim.yaml"]
