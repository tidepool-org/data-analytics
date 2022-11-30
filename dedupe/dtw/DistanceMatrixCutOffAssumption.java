import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.util.Scanner;

public class DistanceMatrixCutOffAssumption
{
	static int[] ZeroCounter; //static members of the class which can be accessed anywhere
	static int[][] DistanceMatrix;
	static int[] LongestZeroString;
	static int[][] LZScoordinates;
	static int[] DataSetX;
  	static int[] DataSetY;



	public static void main(String[] args) throws FileNotFoundException 
	{

//QUICK TEST CASES
		// int[] ArrayY = new int[]{1,1,2,2,1,1};//set of values that should have different LongestZeroString and ZeroCounter
		// int[] ArrayX = new int[]{1,2,2,2,0,1,1,1};

	// int[] ArrayX = new int[]{1,1,2,3,2,1,0,1};//set of values that should have different LongestZeroString and ZeroCounter
	// int[] ArrayY = new int[]{0,1,1,2,3,2,1,1,3,1,2};

		//{0,0,0,1,1};//
		//{0,0,1,1,0};//


		   int[] ArrayY = new int[]{1,2,1,1,2,4,4,3}; 
		   int[] ArrayX = new int[]{1,1,1,2,4,4,3,2,2,3,4,5};

		// int[] ArrayX = new int[]{2,2,3,3,2,2,2,2,2}; //set of values that should have different LongestZeroString and ZeroCounter
	 // int[] ArrayY = new int[]{2,2,2,3,2,2};

		 // int[] ArrayX = new int[]{3,2,3,1}; //GOOD example of finding starting coordinates of starting positions
		 // int[] ArrayY = new int[]{2,3,1,3,1,3,4,1};
		// int[] ArrayX = new int[]{80,82,85,85,94,90,90,75,77,80,81};
		// int[] ArrayY = new int[]{75,77,80,82,85,85,85,89,94,90,90};
		

		 FileInputStream data = new FileInputStream("/Users/samuelrapp/Desktop/DM/datasetTest.txt"); //X
  	    FileInputStream data2 = new FileInputStream("/Users/samuelrapp/Desktop/DM/dataset2Test.txt"); //Y
         Scanner scanner = new Scanner(data);
         Scanner scanner2 = new Scanner(data2);

        DataSetX = new int[11044];//I looked at the number of lines in the file
        DataSetY = new int[11044];
         DataSetX = ArrayX;
        DataSetY = ArrayY;

        // int i = 0;
        // while(scanner.hasNextLine())
        //     {
                      
        //         DataSetX[i] = scanner.nextInt();
        //         DataSetY[i] = scanner2.nextInt();
               
        //         i++;
        //     } 
        // scanner.close();
        // scanner2.close();



		int HorizontalTraversals = DataSetX.length+DataSetY.length-1;
		ZeroCounter = new int[HorizontalTraversals]; //count total zero/matchs in each diagonal traversal 
		LongestZeroString = new int[HorizontalTraversals]; //tallys the longest continious string of zeros found in any given traversal
		LZScoordinates = new int[HorizontalTraversals][2];//records coordinates(in 2 column matrix) 0 index is X pos, 1 index is Y pos (seems reversed for some reason)


		
				DistanceMatrix = new int[DataSetY.length][DataSetX.length]; //row then columns (incrementing the X values chances the column)
				PrintMatrix(DistanceMatrix);
				DisMatrixFillingDiagonally(DataSetY,DataSetX);
			//	PrintMatrix(DistanceMatrix); //just a basic print function
			//	PrintMatrix(LZScoordinates);
				System.out.println("RESULT SECTION:");
				System.out.println("1. Array index of most zeros: " + getIndexOfLargest(ZeroCounter)); //index of most exact overlap(ala most matching values/zeros)
				System.out.println("2. Array index of longest string of zeros: " + getIndexOfLargest(LongestZeroString));
				System.out.println("3. Starting coordinates of the traversal(on the grid edge) with the longest continuous string of zeros: (x,y)_" + GridEdgeCoordinates(LongestZeroString, DistanceMatrix)); //index of most exact overlap(ala most matching values/zeros)
				System.out.println("4. Starting coordinates of the traversal(on the grid edge) with the most total zeros: (x,y)_" + GridEdgeCoordinates(ZeroCounter, DistanceMatrix));//converts the index of greatest traversal to the starting index(on the edge of the grid) of said traversal
				DisMatrixHorizontal(ArrayY,ArrayX);//standard double for loop to create the proper distance matrix- to check agaisnt by horizontal creation
				PrintMatrix(DistanceMatrix);
				
				System.out.println("5. Exact X & Y grid coordinates of longest String of Zeros (x,y)_"+ "(" + LZScoordinates[getIndexOfLargest(LongestZeroString)][0] + "," + LZScoordinates[getIndexOfLargest(LongestZeroString)][1] + ")");
				System.out.println("6. Percentage Match relative to perfect match_(most total zeros)_" + PercentMatch(ZeroCounter,DistanceMatrix) + "%");
				System.out.println("7. Percentage Match relative to perfect match_(longest continous string of zeros)_"  + PercentMatch(LongestZeroString,DistanceMatrix) + "%");

	}

//public static void ReadGoogleSlides()

	public static void DisMatrixFillingDiagonally(int[]DY, int[]DX)
	{//arguemnts are the arrays of data points
		//Xpos = columns Ypos= rows
		int TotalTraversals = DY.length+DX.length-1;  //# of diagonal iterations needed to go through every potential unit of the grid. Its the number of edge points we use
										//13 is the answer for a 7 by 7 grid. 
										//its equal to the number of edge values or length + width - 1	
		int TraversalsStartingonYAxis = TotalTraversals-DX.length;
		int TraversalsStartingonXAxis = TotalTraversals-DY.length;

		int shortersidelength; //determining the longest possible diagonal in the given matrix, ala the length of the shorter data set
		boolean LongerSideY;
		int difference;

		if(TraversalsStartingonYAxis>TraversalsStartingonXAxis) //the Y axis is bigger than the X axis
			{	
				shortersidelength = TraversalsStartingonXAxis+1;
				LongerSideY = true;
			}
		else ////the X axis is bigger than the Y axis
			{
				shortersidelength = TraversalsStartingonYAxis+1;
				LongerSideY = false;
			}

		if(LongerSideY==true) //to make sure I get a positive value when taking the difference.
			{
				difference = TraversalsStartingonYAxis - TraversalsStartingonXAxis;
			}
		else
			{
				difference = TraversalsStartingonXAxis - TraversalsStartingonYAxis;
			}

		//int CutOffPoint = (shortersidelength/2);//setting what value with result in a corner cut off
		int CutOffPoint = (shortersidelength/100);//lower cut off, less traversals removed.

		int XstartPos = 0;
		int YstartPos = 0;
		int traversalsFromMiddle = 0;
		int ZeroCounter = 0; //index of ZeroCounter array- it is the same as the traversalFromMiddle untill TFM is reset after half the grid is filled
		//with evenly sized arrays the X value will always be Odd so we have to account for java rounding down by adding 1
			
		for(int i=0; i<(TraversalsStartingonXAxis+1); i++)//goes through as many times are you need to traverse the middle traversal to the bottom left corner.
			{	
				if(LongerSideY==false) //X is the longer side, so it must be accounted for in the assumption
					{
						if(CutOffPoint>=(shortersidelength+difference-i))//this code would cut off the Matrix from filling itself once the traversal length was less than half the maximum diagonal.
						{
							//System.out.println("Skipped");
							ZeroCounter = ZeroCounter +1;
							continue;
						}
					}
				else
					{
						if(CutOffPoint>=(shortersidelength-i))//this code would cut off the Matrix from filling itself once the traversal length was less than half the maximum diagonal.
						{
							//System.out.println("Skipped:::");
							ZeroCounter = ZeroCounter + 1;
							continue;
						}
					}


				traversalsFromMiddle = MatrixHelper(DY, DX, XstartPos, YstartPos, traversalsFromMiddle, ZeroCounter)+1; //if the Helper returns the traversal count we can use its value even if the method is creating seperate variables
				ZeroCounter++;
				XstartPos = traversalsFromMiddle;
			}

			traversalsFromMiddle=1;
			XstartPos = 0;//give new starting edge index values
			YstartPos = 1;
			
//System.out.println(LongerSideY);

		for(int p=0; p<TraversalsStartingonYAxis; p++) //traversals from 1 above the middle to top right corner.
			{
				if(LongerSideY==false)//X is the longer side, so it doesn't need to be accounted for.
					{
					if(CutOffPoint>=(shortersidelength-p-1))//this code would cut off the Matrix from filling itself once the traversal length was less than half the maximum diagonal.
						{//+-1 because the values start at (0,1) instead of (0,0) in the for loop above. So there are fewer loops to reach the threshhold
							//System.out.println("Skipped->");
							ZeroCounter = ZeroCounter + 1;
							continue;
						}
					}
				else //Y is the longer side so we have to give it more buffer space
					{
						if(CutOffPoint>=(shortersidelength+difference-p-1))//this code would cut off the Matrix from filling itself once the traversal length was less than half the maximum diagonal.
						{
							//System.out.println("Skipped----");
							ZeroCounter = ZeroCounter + 1;
							continue;
						}
					}


				traversalsFromMiddle = MatrixHelper(DY, DX, XstartPos, YstartPos, traversalsFromMiddle, ZeroCounter)+1; 
				ZeroCounter++;
				YstartPos = traversalsFromMiddle;
			}
	}


			/*to know when to make the recursive call A know how many grid positions must be filled before hand and count or B know the final position index you will land at

			if the length/width of the DisMX grid are equal(THE GRID IS A SQUARE) the length of the longest horizontal(corner to corner) requires sidelength amount of sqaure traversals.
			The longest traversal of a grid with sidelength of X is X operations. Starting at position (0,0)
			starting position (0,y) or (y,0) (where sidelength>y>0) takes Sidelength-Y operations to reach its final grid position

			ex with #s: a  7 by 7 grid's longest traversal is 7 operations long(Starting at position 0,0)
			(0,1)=6op (0,2) = 5...(0,6) = 1 same with (1,0)=6op, (2,0)=5op....(6,0)=1op
			longest traversal(starting at 0,0) is maximum the length of the shorter side 
			


			for a sqaure the longest traversal ends at (sidelength, sidelength) (the perfect diagonal)
			starting position (y,0) ends at position (sidelength-1, sidelength-y-1) //moving towards bottom right corner of grid
			starting position (0,x) ends at position (sidelength-x-1, sidelength-1) //moving towards top right corner of grid
			//we do -1 because the side length starts at 1 but the indexing of the grid starts at 0. so we have to adjust
			*/



	public static int MatrixHelper(int[]DY, int[]DX, int Xpos, int Ypos, int traversals, int ZerocIndex)
	{//the matrix helper function does one complete diagonal traversal of the grid
		//It compares values from DY/DX arrays
		//int XstartPos, int YstartPos are starting positions for the traversal
		//traversals is a arguement that keeps the matrix aware of how far it is from the center diagonal
		//ZeroxIndex is the index of the zero counter static array(for data collection) It matches the traversals counter until traversals is reset before the 2nd for loop in DisMatrixFillingDiagonally

		int SidelengthX = DX.length; //.length is the actually amount of positions allocated in memory so index 0-9 is length 10
		int SidelengthY = DY.length;
		boolean test = true;
		int ActiveZeroCounter = 0;

		while(test==true)
				{
				int DistanceValue = (DX[Xpos]-DY[Ypos])*(DX[Xpos]-DY[Ypos]); //the difference between the values squared
				DistanceMatrix[Ypos][Xpos] = DistanceValue;//put value into Matrix

				if(DistanceValue == 0)//found match (maybe pick a larger range ala 2-6 to allow for puedomatch)
					{
				       	ZeroCounter[ZerocIndex] = ZeroCounter[ZerocIndex]+1;//increment index of total zeros in diagonal traversal
				 		ActiveZeroCounter = ActiveZeroCounter+1;
					}
				else //found non zero value
					{
						if(ActiveZeroCounter > LongestZeroString[ZerocIndex])//if the String of zeros currently found is greater than what we have previously found for this traversal
						{
							LongestZeroString[ZerocIndex] = ActiveZeroCounter;//change the value of longest Active Zero counter to the active zero counter
							LZScoordinates[ZerocIndex][0] = (Xpos - ActiveZeroCounter); 
							LZScoordinates[ZerocIndex][1] = (Ypos - ActiveZeroCounter); 

						}
						ActiveZeroCounter = 0; //reset the active counter to zero 
					}

				//leave loop if the array indexs being called match the final position the call reaches
				if(Xpos >= (SidelengthX-1) || Ypos >= (SidelengthY-1))//-1 is because array index starts at zero but side length doesn't.
					{
						if(ActiveZeroCounter > LongestZeroString[ZerocIndex])//Need to check in senario when the traversal ends in a match/zero
							{
								LongestZeroString[ZerocIndex] = ActiveZeroCounter;
								System.out.println(ActiveZeroCounter);
								if(ActiveZeroCounter>0)
								LZScoordinates[ZerocIndex][0] = ((Xpos+1) - ActiveZeroCounter);
								LZScoordinates[ZerocIndex][1] = ((Ypos+1) - ActiveZeroCounter); 
						 //the +1 is needed because the ActiveZeroCounter could potentially give you a negative 'coordinate', 
						 //If the zero string makes it all the way to the bottom, the (X/Ypos-activeZeroCounter) < 0. Not possible
						//It isn't needed for the strings that don't end on the final position on the traversal because the +1s are happening within the while loop. 
							//IE. These coordinates are being calculated during the same loop as the final zero is found, but in the case above the coordinates are being calculated in the loop after the final zero is found.
							}

						test = false;
					}

				Xpos = Xpos+1;
				Ypos = Ypos+1;
				}

		return traversals;		//so we can keep track of the position of the traversal
		//we need to know which travesal we have just done. To know where to start the next one
	}


	public static String GridEdgeCoordinates(int[] array, int[][]Matrix) //Gets starting coordinates of traversal based on largest value in array
	{
		int LargestValueIndex = getIndexOfLargest(array);
		String coordinates;


		if(LargestValueIndex>=(Matrix[1].length))
			{
				coordinates = new String("(" + 0 + "," + ((LargestValueIndex-(Matrix[1].length)+1) +") "+ "value: " + array[LargestValueIndex]));
				//if the starting value was in the top half of the grid
				//this is because the grid is made middle to bottom left corner then back to the middle line to top right corner
			}
		else
			{
				coordinates = new String("(" + LargestValueIndex + "," + 0 + ") " + "value: " + array[LargestValueIndex]);
			} 

		return coordinates;
	}

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

	public static double PercentMatch(int[]Array, int[][]Matrix)
	{ 	//takes in one array, and a matrix. Finds the percent match between largest value in array and shorter sidelength of the matrix.
		//We are determining how many matchs occured(or consequetively or not), in the best case, vs how many could have
		int IndexOfLargest = getIndexOfLargest(Array);
		double ValueTotal;

		//no given traversal is longer than the shorter side of the Matrix-thus the longest traversal is = the shorter sidelength
		if(Matrix.length > Matrix[1].length)
			{
				ValueTotal = Matrix[1].length;
			}
		else
			{
				ValueTotal = Matrix.length;
			}

		double ValueMatchs = (double) Array[IndexOfLargest];
		double PercentMatch = (ValueMatchs/ValueTotal)*100;
		return PercentMatch;
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
			System.out.print("_____________________________________");
			System.out.println();
	}

	public static void DisMatrixHorizontal(int[]X,int[]Y) //standard approach to creating the distance matrix via 2 for loop. horizontal traversal not diagonal
	{
		int[][] DistanceMX = new int[X.length][Y.length];		
		for(int i=0; i<(X.length); i++)
			{
				for(int t=0; t<Y.length; t++)
					{
						System.out.println(i + ", " + t);
						DistanceMX[i][t]=(Y[t]-X[i])*(Y[t]-X[i]);
					}
			}
		PrintMatrix(DistanceMX); //prints the Matrix it creates at the end
	}
	
}


