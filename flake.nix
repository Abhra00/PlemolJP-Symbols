{
  description = "PlemolJP Symbols: symbol fallback for PlemolJP Console";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = {
    self,
    nixpkgs,
  }: let
    systems = ["x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin"];
    forAllSystems = f: nixpkgs.lib.genAttrs systems (system: f nixpkgs.legacyPackages.${system});
    pins = builtins.fromJSON (builtins.readFile ./hashes.json);
    base = "https://github.com/Abhra00/PlemolJP-Symbols/releases/download/${pins.tag}";
  in {
    packages = forAllSystems (pkgs: rec {
      plemoljp-symbols =
        if pins.files == {}
        then throw "hashes.json is empty: run the build workflow first"
        else
          pkgs.stdenvNoCC.mkDerivation {
            pname = "plemoljp-symbols";
            version = pkgs.lib.removePrefix "build-" pins.tag;
            srcs =
              pkgs.lib.mapAttrsToList
              (name: hash: pkgs.fetchurl {
                inherit name hash;
                url = "${base}/${name}";
              })
              pins.files;

            dontUnpack = true;
            dontBuild = true;

            installPhase = ''
              runHook preInstall
              for f in $srcs; do
                name=$(stripHash "$f")
                case "$name" in
                  *.ttf) install -Dm444 "$f" "$out/share/fonts/truetype/$name" ;;
                  *) install -Dm444 "$f" "$out/share/doc/plemoljp-symbols/$name" ;;
                esac
              done
              runHook postInstall
            '';

            meta = {
              description = "Symbol fallback for PlemolJP Console, built from Iosevka";
              license = pkgs.lib.licenses.ofl;
              platforms = pkgs.lib.platforms.all;
            };
          };
      default = plemoljp-symbols;
    });
  };
}
