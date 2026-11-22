{
  description = "C# generator for LinkML schemas";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    uv2nix.url = "github:pyproject-nix/uv2nix";
    uv2nix.inputs.nixpkgs.follows = "nixpkgs";
    pyproject-build-systems.url = "github:pyproject-nix/build-system-pkgs";
    pyproject-build-systems.inputs = {
      nixpkgs.follows = "nixpkgs";
      uv2nix.follows = "uv2nix";
      pyproject-nix.follows = "uv2nix/pyproject-nix";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      uv2nix,
      pyproject-build-systems,
      ...
    }:
    let
      forAllSystems = nixpkgs.lib.genAttrs [
        "x86_64-linux"
        "aarch64-linux"
      ];
      inherit (uv2nix.inputs) pyproject-nix;
      workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
    in
    {
      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          pythonSet =
            (pkgs.callPackage pyproject-nix.build.packages { python = pkgs.python3; }).overrideScope
              (
                pkgs.lib.composeManyExtensions [
                  pyproject-build-systems.overlays.wheel
                  (workspace.mkPyprojectOverlay { sourcePreference = "wheel"; })
                ]
              );
          inherit (pkgs.callPackages pyproject-nix.build.util { }) mkApplication;
        in
        {
          default = mkApplication {
            venv = pythonSet.mkVirtualEnv "linkml-csharp-env" workspace.deps.default;
            package = pythonSet.linkml-csharp;
          };
        }
      );

      checks = forAllSystems (system: {
        gen-csharp =
          nixpkgs.legacyPackages.${system}.runCommand "check-gen-csharp"
            {
              nativeBuildInputs = [ self.packages.${system}.default ];
            }
            ''
              gen-csharp ${./tests/input/kitchen_sink.yaml} -d "$out" --namespace Golden
              diff -ru ${./tests/golden/kitchen_sink} "$out"
            '';
      });

      devShells = forAllSystems (
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
              export LD_LIBRARY_PATH="${
                pkgs.lib.makeLibraryPath [ pkgs.stdenv.cc.cc.lib ]
              }''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
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
