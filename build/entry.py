"""Script de entrada para PyInstaller.

PyInstaller necesita un archivo-script como punto de entrada; este solo delega en
``sisav2_mcp.app.main`` para no duplicar la lógica del entry dual.
"""

from sisav2_mcp.app import main

if __name__ == "__main__":
    main()
