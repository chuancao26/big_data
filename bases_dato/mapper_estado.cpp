#include <iostream>
#include <string>
#include <sstream>
#include <vector>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string line;
    while (getline(cin, line)) {
        if (line.empty()) continue;

        stringstream ss(line);
        string token;
        vector<string> columns;
        
        while (getline(ss, token, '\t')) {
            columns.push_back(token);
        }
        
        if (columns.size() >= 11) {
            string mesa = columns[0];
            string idEleccion = columns[1];
            string idAmbito = columns[2];
            string estadoActa = columns[4];
            
            // Ignorar cabeceras o filas vacías
            if (mesa.empty() || mesa == "codigoMesa" || idEleccion.empty()) continue;

            // CLAVE: idEleccion|idAmbito|estadoActa
            // VALOR: mesa
            cout << idEleccion << "|" << idAmbito << "|" << estadoActa << "\t" << mesa << "\n";
        }
    }
    return 0;
}
