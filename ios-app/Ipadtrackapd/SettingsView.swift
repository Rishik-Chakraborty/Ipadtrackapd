import SwiftUI

struct SettingsView: View {
    @Binding var serverURL: String
    @Binding var isPresented: Bool
    
    @State private var draftURL: String = ""
    
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Server Connection")) {
                    TextField("http://<hostname>.local:8765", text: $draftURL)
                        .keyboardType(.URL)
                        .autocapitalization(.none)
                        .disableAutocorrection(true)
                }
                
                Section(footer: Text("If the auto-discovered .local hostname doesn't work, type the exact IP address printed by the server (e.g. http://192.168.1.5:8765)")) {
                    Button("Save & Reload") {
                        serverURL = draftURL
                        isPresented = false
                    }
                    .disabled(draftURL.isEmpty)
                }
            }
            .navigationTitle("Settings")
            .navigationBarItems(trailing: Button("Cancel") {
                isPresented = false
            })
            .onAppear {
                draftURL = serverURL
            }
        }
    }
}
