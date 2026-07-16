import SwiftUI

struct ContentView: View {
    @AppStorage("serverURL") var serverURL: String = ""
    @State private var showingSettings = false
    
    var body: some View {
        ZStack {
            Color.black.edgesIgnoringSafeArea(.all)
            
            if serverURL.isEmpty {
                VStack {
                    Text("Welcome to Ipadtrackapd")
                        .font(.largeTitle)
                        .foregroundColor(.white)
                        .padding()
                    Button("Configure Server") {
                        showingSettings = true
                    }
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                }
            } else {
                WebViewContainer(url: serverURL)
                    .edgesIgnoringSafeArea(.all)
            }
            
            VStack {
                Spacer()
                HStack {
                    Spacer()
                    Button(action: {
                        showingSettings = true
                    }) {
                        Image(systemName: "gear")
                            .font(.system(size: 24))
                            .foregroundColor(.gray.opacity(0.5))
                            .padding()
                    }
                }
            }
        }
        .sheet(isPresented: $showingSettings) {
            SettingsView(serverURL: $serverURL, isPresented: $showingSettings)
        }
    }
}
