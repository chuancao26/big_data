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
            string idEleccion = columns[1];
            string idAmbito = columns[2];  // 1=Nacional, 2=Internacional
            string idUbigeo = columns[3];
            string partido = columns[9];
            string votos = columns[10];
            
            if (partido.empty() || idEleccion.empty() || idEleccion == "idEleccion" || idUbigeo.empty() || idUbigeo == "idUbigeo") continue;

            if (idUbigeo.length() > 0 && idUbigeo.length() < 6) {
                idUbigeo = string(6 - idUbigeo.length(), '0') + idUbigeo;
            }

            string region = "00";
            if (idUbigeo.length() >= 2) {
                region = idUbigeo.substr(0, 2);
            }

            cout << idEleccion << "|" << idAmbito << "|" << region << "|" << partido << "\t" << votos << "\n";
        }
    }
    return 0;
}
