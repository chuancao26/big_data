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
        
        // Validar que tengamos la estructura de 14 columnas
        if (columns.size() >= 14) {
            string idEleccion = columns[1];
            string idAmbito = columns[2];  // 1=Nacional, 2=Internacional
            string departamento = columns[4]; // Usamos la nueva columna de departamento directo
            string partido = columns[12];
            string votos = columns[13];
            
            // Ignorar cabeceras o registros corruptos
            if (partido.empty() || idEleccion.empty() || idEleccion == "idEleccion" || departamento.empty()) continue;

            // Decodificar el tipo de elección
            string nombreEleccion = idEleccion;
            if (idEleccion == "10") nombreEleccion = "PRESIDENCIAL";
            else if (idEleccion == "14") nombreEleccion = "DIPUTADOS";
            else if (idEleccion == "12") nombreEleccion = "SEN_NACIONALES";
            else if (idEleccion == "13") nombreEleccion = "SEN_REGIONALES";
            else if (idEleccion == "15") nombreEleccion = "PARLAMENTO";

            // NUEVA CLAVE COMPUESTA: idEleccion|idAmbito|departamento|partido
            cout << nombreEleccion << "|" << idAmbito << "|" << departamento << "|" << partido << "\t" << votos << "\n";
        }
    }
    return 0;
}
