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
        
        // Separar la linea por tabuladores (\t)
        while (getline(ss, token, '\t')) {
            columns.push_back(token);
        }
        
        // Validar que tengamos la estructura completa
        if (columns.size() >= 11) {
            string idEleccion = columns[1];
            string idAmbito = columns[2];  // 1=Nacional, 2=Internacional
            string idUbigeo = columns[3];
            string partido = columns[9];
            string votos = columns[10];
            
            // Ignorar cabeceras o registros corruptos
            if (partido.empty() || idEleccion.empty() || idEleccion == "idEleccion" || idUbigeo.empty() || idUbigeo == "idUbigeo") continue;

            // --- LÓGICA DE UBIGEO PARA PROVINCIA ---
            // 1. Rellenar con ceros a la izquierda si tiene menos de 6 caracteres
            if (idUbigeo.length() > 0 && idUbigeo.length() < 6) {
                idUbigeo = string(6 - idUbigeo.length(), '0') + idUbigeo;
            }

            // 2. Extraer los primeros 4 dígitos (Región + Provincia)
            string provincia = "0000";
            if (idUbigeo.length() >= 4) {
                provincia = idUbigeo.substr(0, 4);
            } else {
                provincia = idUbigeo; 
            }

            // NUEVA CLAVE COMPUESTA: idEleccion|idAmbito|Provincia|Partido
            cout << idEleccion << "|" << idAmbito << "|" << provincia << "|" << partido << "\t" << votos << "\n";
        }
    }
    return 0;
}
