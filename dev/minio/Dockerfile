# Isolated compatibility-test server only. Upstream community MinIO is archived;
# build its pinned source because precompiled community releases are unavailable.
FROM golang:1.25-bookworm AS build
ARG MINIO_COMMIT=07c3a429bfed433e49018cb0f78a52145d4bedeb
WORKDIR /src
RUN git init . && git remote add origin https://github.com/minio/minio.git \
    && git fetch --depth 1 origin "$MINIO_COMMIT" && git checkout --detach FETCH_HEAD
RUN CGO_ENABLED=0 go build -trimpath -o /out/minio .

FROM alpine:3.22
RUN adduser -D -u 10001 storage && mkdir /data && chown storage:storage /data
COPY --from=build /out/minio /usr/local/bin/minio
USER storage
ENV MINIO_UPDATE=off
EXPOSE 9000
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--address", ":9000"]
