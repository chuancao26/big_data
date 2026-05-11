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
        if (columns.size() >= 11) {
            string idEleccion = columns[1];
            string partido = columns[9];
            string votos = columns[10];
            
            // Ignorar cabeceras o registros vacios
            if (partido.empty() || idEleccion.empty() || idEleccion == "idEleccion") continue;

            // NUEVA CLAVE COMPUESTA: idEleccion|partido
            cout << idEleccion << "|" << partido << "\t" << votos << "\n";
        }
    }
    return 0;
}
