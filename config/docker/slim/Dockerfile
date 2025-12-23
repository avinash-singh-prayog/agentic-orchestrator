# SLIM Transporter with baked-in configuration
# Base image from AGNTCY
FROM ghcr.io/agntcy/slim:0.6.1

# Copy configuration file to the expected path
COPY slim.yaml /etc/slim.yaml

# Expose both SLIM ports
# 46357: Primary transport
# 46358: Secondary (health/metrics)
EXPOSE 46357 46358

# Run SLIM with the config
ENTRYPOINT ["/slim"]
CMD ["--config", "/etc/slim.yaml"]
