#include <iostream>
#include <string>
#include <unordered_set>
#include <algorithm>

using namespace std;

// Función para cambiar los pipes '|' por tabuladores '\t'
string formatearClave(string key) {
    replace(key.begin(), key.end(), '|', '\t');
    return key;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    string line;
    string current_key = "";
    
    // El set nos garantiza que no haya mesas duplicadas
    unordered_set<string> mesas_unicas; 

    while (getline(cin, line)) {
        size_t tab_pos = line.find('\t');
        if (tab_pos == string::npos) continue;

        string key = line.substr(0, tab_pos);
        string mesa = line.substr(tab_pos + 1);

        // Lógica de agrupación
        if (current_key != key) {
            if (!current_key.empty()) {
                // Al cambiar de grupo, imprimimos el tamaño del set (el count)
                cout << formatearClave(current_key) << "\t" << mesas_unicas.size() << "\n";
            }
            current_key = key;
            mesas_unicas.clear(); // Limpiamos el set para el nuevo grupo
        }
        
        // Insertamos la mesa (si ya existe en el set, C++ simplemente la ignora)
        mesas_unicas.insert(mesa);
    }
    
    // Imprimir el último grupo al terminar el archivo
    if (!current_key.empty()) {
        cout << formatearClave(current_key) << "\t" << mesas_unicas.size() << "\n";
    }

    return 0;
}
