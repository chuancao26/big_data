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
        
        // Validar que tengamos la estructura completa de nuestro ETL
        if (columns.size() >= 14) {
            string idEleccion = columns[1];
            string idAmbito = columns[2];
            string partido = columns[12];
            string votos = columns[13];
            
            // Ignorar cabeceras o registros vacios
            if (partido.empty() || idEleccion.empty() || idEleccion == "idEleccion") continue;

            // NUEVA CLAVE COMPUESTA: idEleccion|idAmbito|partido
            cout << idEleccion << "|" << idAmbito << "|" << partido << "\t" << votos << "\n";
        }
    }
    return 0;
}
