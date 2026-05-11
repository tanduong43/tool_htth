
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
            "       System.out.println(\"API Server OK: Port 8888\"); " +
            "       while(true) { " +
            "           java.net.Socket s = ss.accept(); " +
            "           s.getOutputStream().write(\"HTTP/1.1 200 OK\\r\\n\\r\\n{\\\"status\\\":\\\"OK\\\",\\\"message\\\":\\\"Server Dang Chay\\\"}\".getBytes()); " +
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
