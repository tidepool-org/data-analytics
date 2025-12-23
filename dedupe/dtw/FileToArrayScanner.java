import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.util.Scanner;



public class FileToArrayScanner {

  static int[]DataSet;
  static int[]DataSet2;


    public static void main(String args[]) throws FileNotFoundException
    {
        FileInputStream data = new FileInputStream("/Users/srapp/Desktop/dataset.txt");
        FileInputStream data2 = new FileInputStream("/Users/srapp/Desktop/dataset2.txt");
        Scanner scanner = new Scanner(data);
        Scanner scanner2 = new Scanner(data2);

        DataSet = new int[11044];//I looked at the number of lines in the file
        DataSet2 = new int[11044];

        int i = 0;
        while(scanner.hasNextLine())
            {
               // System.out.println(scanner.nextLine());  
                //System.out.println(scanner.nextInt());          
                DataSet[i] = scanner.nextInt();
                DataSet2[i] = scanner2.nextInt();
                System.out.println(DataSet[i]+"!1");
                System.out.println(DataSet2[i]+"!2");
                i++;
            } 
        scanner.close();
        scanner2.close();
    }   
      
}
