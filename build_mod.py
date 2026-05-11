import os
import sys
import urllib.request
import zipfile
import subprocess

# Cấu hình
JAR_URL = "https://repo1.maven.org/maven2/org/javassist/javassist/3.29.2-GA/javassist-3.29.2-GA.jar"
JAVASSIST_JAR = "javassist.jar"
INJECTOR_JAVA = "HTTH_Injector.java"
INPUT_GAME = "HaiTacTiHon_v129_b365_21_10_2025.jar"
OUTPUT_GAME = "HaiTacTiHon_Modded_API.jar"

# Mã nguồn Java Injector (Dùng để tiêm Server API vào game gốc)
JAVA_CODE = """
import javassist.*;
import java.io.*;
import java.util.Enumeration;
import java.util.jar.*;

public class HTTH_Injector {
    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.out.println("Usage: java HTTH_Injector <input.jar> <output.jar> <mainClass>");
            return;
        }
        String inputJar = args[0];
        String outputJar = args[1];
        String mainClass = args[2];

        ClassPool pool = ClassPool.getDefault();
        pool.insertClassPath(inputJar);

        System.out.println("[*] Dang tao Local API Server (Port 8888)...");
        
        // Tạo class mới cho Server để tránh lỗi biên dịch nội tuyến của Javassist
        CtClass serverThread = pool.makeClass("HTTHLocalServer");
        serverThread.getClassFile().setMajorVersion(52); // Ép xuống Java 8 (version 52.0)
        serverThread.getClassFile().setMinorVersion(0);
        serverThread.addInterface(pool.get("java.lang.Runnable"));
        
        String runBody = 
            "public void run() { " +
            "   try { " +
            "       java.net.ServerSocket ss = new java.net.ServerSocket(8888); " +
            "       System.out.println(\\\"API Server OK: Port 8888\\\"); " +
            "       while(true) { " +
            "           java.net.Socket s = ss.accept(); " +
            "           s.getOutputStream().write(\\\"HTTP/1.1 200 OK\\\\r\\\\n\\\\r\\\\n{\\\\\\\"status\\\\\\\":\\\\\\\"OK\\\\\\\",\\\\\\\"message\\\\\\\":\\\\\\\"Server Dang Chay\\\\\\\"}\\\".getBytes()); " +
            "           s.close(); " +
            "       } " +
            "   } catch(Exception e) { e.printStackTrace(); } " +
            "}";
        
        CtMethod runMethod = CtNewMethod.make(runBody, serverThread);
        serverThread.addMethod(runMethod);
        
        File tempDir = new File("mod_temp");
        tempDir.mkdirs();
        serverThread.writeFile(tempDir.getAbsolutePath());

        System.out.println("[*] Dang tim class: " + mainClass);
        CtClass cc = pool.get(mainClass);
        
        // Tuy theo game J2ME, ham khoi dong thuong la startApp()
        CtMethod m = cc.getDeclaredMethod("startApp");
        
        System.out.println("[*] Tien hanh Tiem Bytecode vao: startApp()...");
        m.insertBefore("new Thread(new HTTHLocalServer()).start();");
        cc.writeFile(tempDir.getAbsolutePath());

        System.out.println("[*] Dang dong goi lai thanh: " + outputJar);
        
        JarFile jar = new JarFile(inputJar);
        JarOutputStream jos = new JarOutputStream(new FileOutputStream(outputJar));
        Enumeration<JarEntry> entries = jar.entries();
        
        while(entries.hasMoreElements()) {
            JarEntry entry = entries.nextElement();
            if (entry.getName().equals("META-INF/HTTH.SF") || entry.getName().equals("META-INF/HTTH.RSA") || entry.getName().equals("META-INF/MANIFEST.MF")) {
                if (entry.getName().equals("META-INF/HTTH.SF") || entry.getName().equals("META-INF/HTTH.RSA")) {
                    continue; // Bo qua chu ky dien tu cu
                }
            }
            jos.putNextEntry(new JarEntry(entry.getName()));
            
            File moddedFile = new File(tempDir, entry.getName());
            if (moddedFile.exists()) {
                FileInputStream fis = new FileInputStream(moddedFile);
                byte[] buffer = new byte[1024];
                int bytesRead;
                while ((bytesRead = fis.read(buffer)) != -1) {
                    jos.write(buffer, 0, bytesRead);
                }
                fis.close();
            } else {
                InputStream is = jar.getInputStream(entry);
                byte[] buffer = new byte[1024];
                int bytesRead;
                while ((bytesRead = is.read(buffer)) != -1) {
                    jos.write(buffer, 0, bytesRead);
                }
                is.close();
            }
            jos.closeEntry();
        }
        
        // Thêm class HTTHLocalServer vừa tạo vào jar
        jos.putNextEntry(new JarEntry("HTTHLocalServer.class"));
        FileInputStream fis = new FileInputStream(new File(tempDir, "HTTHLocalServer.class"));
        byte[] buffer = new byte[1024];
        int bytesRead;
        while ((bytesRead = fis.read(buffer)) != -1) { jos.write(buffer, 0, bytesRead); }
        fis.close();
        jos.closeEntry();
        
        jos.close();
        jar.close();
        System.out.println("[*] THANH CONG! File Mod da duoc tao: " + outputJar);
    }
}
"""

def download_javassist():
    if not os.path.exists(JAVASSIST_JAR):
        print("[+] Dang tai thu vien Javassist...")
        urllib.request.urlretrieve(JAR_URL, JAVASSIST_JAR)
        print("[+] Tai thanh cong javassist.jar!")

def get_main_class(jar_path):
    print(f"[+] Dang doc MANIFEST.MF tu {jar_path}...")
    try:
        with zipfile.ZipFile(jar_path, 'r') as z:
            with z.open('META-INF/MANIFEST.MF') as f:
                content = f.read().decode('utf-8', errors='ignore')
                for line in content.split('\n'):
                    line = line.strip()
                    if line.lower().startswith('midlet-1:'):
                        # Dòng này có dạng: MIDlet-1: Name, Icon, ClassName
                        parts = line.split(',')
                        if len(parts) >= 3:
                            return parts[2].strip()
                
                print("[!] KHONG TIM THAY MIDlet-1. NOI DUNG MANIFEST LA:")
                print("-" * 30)
                print(content)
                print("-" * 30)
    except Exception as e:
        print(f"Loi khi doc MANIFEST: {e}")
    return None

def build():
    if not os.path.exists(INPUT_GAME):
        print(f"[!] LỖI: Khong tim thay file {INPUT_GAME}")
        return

    main_class = get_main_class(INPUT_GAME)
    if not main_class:
        print("[!] LỖI: Khong the xac dinh Main Class cua game.")
        return
    print(f"[+] Tim thay Main Class: {main_class}")

    download_javassist()

    print("[+] Dang tao HTTH_Injector.java...")
    with open(INJECTOR_JAVA, "w", encoding="utf-8") as f:
        f.write(JAVA_CODE)

    print("[+] Dang bien dich HTTH_Injector.java (Yeu cau co san JDK)...")
    cp_sep = ";" if os.name == "nt" else ":"
    compile_cmd = f"javac -encoding utf8 -cp {JAVASSIST_JAR} {INJECTOR_JAVA}"
    
    res = subprocess.run(compile_cmd, shell=True)
    if res.returncode != 0:
        print("\\n[!] LỖI BIÊN DỊCH: Trình biên dịch Java (javac) báo lỗi.")
        print("    Vui lòng kiểm tra lại lỗi ở trên!")
        return

    print("[+] Dang chay HTTH_Injector de Tiem Code vao Game...")
    run_cmd = f"java -cp .{cp_sep}{JAVASSIST_JAR} HTTH_Injector {INPUT_GAME} {OUTPUT_GAME} {main_class}"
    subprocess.run(run_cmd, shell=True)

if __name__ == "__main__":
    print("="*50)
    print("   TOOL BUILD BẢN MOD HTTH (LOCAL API SERVER)")
    print("="*50)
    build()
