#include <iostream>
#include <string>
#include <algorithm>

using namespace std;

// Funcion para cambiar los pipes '|' por tabuladores '\t' para el TSV final
string formatearClave(string key) {
    replace(key.begin(), key.end(), '|', '\t');
    return key;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string line;
    string current_key = "";
    long long current_sum = 0;

    while (getline(cin, line)) {
        size_t tab_pos = line.find('\t');
        if (tab_pos == string::npos) continue;

        string key = line.substr(0, tab_pos);
        string str_votos = line.substr(tab_pos + 1);
        
        long long votos = 0;
        try {
            votos = stoll(str_votos);
        } catch (...) {
            continue; // Ignorar si no es un numero
        }

        // Lógica de agrupacion de Hadoop
        if (current_key == key) {
            current_sum += votos;
        } else {
            if (!current_key.empty()) {
                // Imprimir: idEleccion \t idUbigeo \t Partido \t Votos_Sumados
                cout << formatearClave(current_key) << "\t" << current_sum << "\n";
            }
            current_key = key;
            current_sum = votos;
        }
    }
    
    // Imprimir el ultimo grupo
    if (!current_key.empty()) {
        cout << formatearClave(current_key) << "\t" << current_sum << "\n";
    }

    return 0;
}
