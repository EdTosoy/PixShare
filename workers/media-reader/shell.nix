{ pkgs ? import <nixpkgs> { } }:

# Optional NixOS development shell. Do not patch pnpm's shared-store binaries.
pkgs.mkShell {
  MINIFLARE_WORKERD_PATH = pkgs.writeShellScript "pixshare-workerd" ''
    workerd_binary=$(node -p 'require(require.resolve("workerd", { paths: [require.resolve("wrangler")] })).default')
    exec ${pkgs.glibc}/lib/ld-linux-x86-64.so.2 "$workerd_binary" "$@"
  '';
}
