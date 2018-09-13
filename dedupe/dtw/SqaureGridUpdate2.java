public class SqaureGridUpdate2
{

	public static int getIndexOfLargest(int[] array)	//returns index of largest value in an array
	{
	 	 if(array == null || array.length == 0) 
	 	 	{
		 	 	return -1; // null or empty
		 	}

         int largest = 0;
		 	 
		 for(int i = 1; i<array.length; i++)
		  	{
		    	if(array[i]>array[largest])
				   { 
				   	    largest = i;
				   }
		  	}

	  return largest; 
	}




	public static void MatchArrays(int[]Array1, int[]Array2)
	{
		if(Array1.length>Array2.length)
			{
				int[] Temp = new int[Array1.length];
				for(int i = 0; i<Array2.length; i++)
					{
						Temp[i]=Array2[i];
					}
			
			    System.arraycopy(Temp, 0, Array2, 0, Temp.length);
			}
		else if(Array1.length<Array2.length)
			{
				int[] Temp = new int[Array2.length];
				for(int i = 0; i<Array1.length; i++)
					{
						Temp[i]=Array1[i];
					}
			
				System.arraycopy(Temp, 0, Array1, 0, Temp.length); 
			}

		System.out.println(Array1.length + "," + Array2.length);//a check to see if the arrays are equal length now
	}





	public static void DisMatrixCreater(int[]X,int[]Y) //standard approach to creating the distance matrix via 2 for loop. horizontal traversal not diagonal
	{
		int[][] DistanceMX = new int[Y.length][X.length];		
		for(int i=0; i<X.length; i++)
			{
				for(int t=0; t<Y.length; t++)
					{
						DistanceMX[i][t]=(Y[t]-X[i])*(Y[t]-X[i]);
					}
			}
		PrintMatrix(DistanceMX); //prints the Matrix it creates at the end
	}



	public static void PrintMatrix(int[][]Matrix) //prints the Distance Matrix given a Matrix
	{//Print out the  matrix in nice
		for (int i = 0; i < Matrix.length; i++)
			{ 
			   	for (int j = 0; j < Matrix[i].length; j++) 
				   	{
				    	System.out.print(Matrix[i][j] + " | ");
			    	}
		    	System.out.println();
			}
	}




}