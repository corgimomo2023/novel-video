FROM runpod/worker-comfyui:5.8.6-base

LABEL org.opencontainers.image.title="novel-video-wan-s2v-worker" \
      org.opencontainers.image.description="Wan2.2 S2V worker for video.example.com" \
      org.opencontainers.image.source="https://github.com/corgimomo2023/novel-video"

COPY workflows/ /opt/novel-video/workflows/
COPY models.json /opt/novel-video/models.json

ENV COMFY_LOG_LEVEL=INFO \
    NETWORK_VOLUME_DEBUG=false \
    REFRESH_WORKER=false

# Native Wan2.2 S2V uses ComfyUI core nodes only. Models are mounted from
# /runpod-volume/models to avoid a 23.5 GiB model layer and slow image pulls.
CMD ["/start.sh"]
