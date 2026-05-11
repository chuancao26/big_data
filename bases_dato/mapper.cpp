#include <iostream>
#include <string>
#include <sstream>
#include <vector>

using namespace std;

int main() {
    // Optimizacion para lectura rapida en consola
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string line;
    while (getline(cin, line)) {
        if (line.empty()) continue;

        stringstream ss(line);
        string token;
        vector<string> columns;
        
        // Separar la linea por tabuladores (\t)
        while (getline(ss, token, '\t')) {
            columns.push_back(token);
        }
        
        // Validar que la fila tenga las 11 columnas
        if (columns.size() >= 11) {
            string idEleccion = columns[1];
            string idUbigeo = columns[3];
            string partido = columns[9];
            string votos = columns[10];
            
            // Ignorar cabeceras o registros corruptos
            if (idUbigeo == "idUbigeo" || idUbigeo.empty() || partido.empty() || idEleccion.empty()) continue;

            // NUEVA CLAVE COMPUESTA: idEleccion|idUbigeo|partido
            cout << idEleccion << "|" << idUbigeo << "|" << partido << "\t" << votos << "\n";
        }
    }
    return 0;
}
