{
  description = "C# generator for LinkML schemas";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { nixpkgs, ... }:
    {
      devShells =
        nixpkgs.lib.genAttrs
          [
            "x86_64-linux"
            "aarch64-linux"
          ]
          (
            system:
            let
              pkgs = nixpkgs.legacyPackages.${system};
            in
            {
              default = pkgs.mkShell {
                packages = [
                  pkgs.uv
                  pkgs.python314
                  pkgs.python311 # oldest Python in nixpkgs; CI also covers 3.10
                  pkgs.ruff # the ruff wheel installed by uv cannot run on NixOS
                  pkgs.pre-commit
                  pkgs.dotnet-sdk_10
                  (pkgs.writeShellScriptBin "golden" ''
                    exec ${pkgs.uv}/bin/uv run pytest tests/test_golden.py "$@"
                  '')
                ];
                # PyOxigraph's PyPI wheel needs the C++ runtime at import time.
                shellHook = ''
                  export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ]}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
                '';
                # uv's downloaded interpreters cannot run on NixOS: use the ones above.
                UV_PYTHON_DOWNLOADS = "never";
                DOTNET_CLI_TELEMETRY_OPTOUT = "1";
                DOTNET_NOLOGO = "1";
              };
            }
          );
    };
}
