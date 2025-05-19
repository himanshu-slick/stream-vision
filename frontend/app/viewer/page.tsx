'use client';

import { useState, useEffect, useRef, createRef } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import {
	Card,
	CardContent,
	CardDescription,
	CardFooter,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
	Eye,
	ArrowLeft,
	Play,
	Plus,
	X,
	Maximize,
	Minimize,
} from 'lucide-react';
import { useMobile } from '@/hooks/use-mobile';
import { ThemeToggle } from '@/components/theme-toggle';
import { ScrollArea } from '@/components/ui/scroll-area';
import { startHLSStream, getHLSStreamUrl } from '@/lib/api';
import Hls from 'hls.js';

// Define the stream type
type Stream = {
	id: string;
	url: string;
	username: string;
	password: string;
	isExpanded: boolean;
	streamId?: string;
	videoRef: React.RefObject<HTMLVideoElement | null>;
	hlsInitialized?: boolean;
};

export default function ViewerPage() {
	const [streams, setStreams] = useState<Stream[]>([]);
	const [showAddForm, setShowAddForm] = useState(true);
	const [newStream, setNewStream] = useState<
		Omit<Stream, 'id' | 'isExpanded' | 'videoRef'>
	>({
		url: '',
		username: '',
		password: '',
	});
	const isMobile = useMobile();

	useEffect(() => {
		streams.forEach((stream) => {
			if (
				stream.streamId &&
				!stream.hlsInitialized &&
				stream.videoRef &&
				stream.videoRef.current
			) {
				console.log(
					`[useEffect] Initializing HLS for stream ID: ${stream.streamId} on video element:`,
					stream.videoRef.current
				);
				initializeHLS(stream.videoRef.current, stream.streamId);
				setStreams((prevStreams) =>
					prevStreams.map((s) =>
						s.id === stream.id ? { ...s, hlsInitialized: true } : s
					)
				);
			}
		});
	}, [streams]);

	// Initialize HLS stream
	const initializeHLS = (videoElement: HTMLVideoElement, streamId: string) => {
		console.log(`[initializeHLS] Called for streamId: ${streamId}`);
		if (Hls.isSupported()) {
			const hls = new Hls();
			const hlsUrl = getHLSStreamUrl(streamId);
			console.log(`[initializeHLS] Hls.js: Loading source URL: ${hlsUrl}`);
			hls.loadSource(hlsUrl);
			hls.attachMedia(videoElement);
			hls.on(Hls.Events.MANIFEST_PARSED, () => {
				videoElement.play().catch((error) => {
					console.error('Error playing video:', error);
				});
			});

			// HLS.js error handling
			hls.on(Hls.Events.ERROR, function (event, data) {
				console.error('[HLS.js ErrorEvent]', data);
				if (data.fatal) {
					switch (data.type) {
						case Hls.ErrorTypes.NETWORK_ERROR:
							console.error(
								'HLS.js fatal network error encountered',
								data.details,
								data
							);
							// E.g., try to recover network error
							hls.startLoad();
							break;
						case Hls.ErrorTypes.MEDIA_ERROR:
							console.error(
								'HLS.js fatal media error encountered',
								data.details,
								data
							);
							hls.recoverMediaError();
							break;
						default:
							console.error(
								'HLS.js an unknown fatal error type occurred',
								data.details,
								data
							);
							hls.destroy();
							break;
					}
				}
			});
		} else if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
			const nativeHlsUrl = getHLSStreamUrl(streamId);
			console.log(
				`[initializeHLS] Native HLS: Setting video src to URL: ${nativeHlsUrl}`
			);
			videoElement.src = nativeHlsUrl;
			videoElement.addEventListener('loadedmetadata', () => {
				videoElement.play().catch((error) => {
					console.error('Error playing video:', error);
				});
			});

			// Native HLS error handling
			videoElement.addEventListener('error', (e) => {
				console.error(
					'[Native HLS ErrorEvent] Error playing video with native HLS.',
					e
				);
				if (videoElement.error) {
					console.error('  Video Element Error Code:', videoElement.error.code);
					console.error(
						'  Video Element Error Message:',
						videoElement.error.message
					);
				}
			});
		}
	};

	// Add a new stream
	const handleAddStream = async (e: React.FormEvent) => {
		e.preventDefault();
		if (newStream.url) {
			console.log('Adding stream with URL:', newStream.url);
			try {
				console.log(
					'[handleAddStream] Calling startHLSStream with:',
					newStream
				);
				const response = await startHLSStream(
					newStream.url,
					newStream.username,
					newStream.password
				);
				const streamId = `stream-${Date.now()}`;
				const videoRef = createRef<HTMLVideoElement>();

				setStreams([
					...streams,
					{
						...newStream,
						id: streamId,
						isExpanded: false,
						streamId: response.stream_id,
						videoRef,
						hlsInitialized: false, // Initialize the flag
					},
				]);

				console.log(
					'[handleAddStream] Backend response for startHLSStream:',
					response
				);

				setNewStream({ url: '', username: '', password: '' });

				// Hide the form on mobile after adding a stream
				if (isMobile && streams.length > 0) {
					setShowAddForm(false);
				}
			} catch (error) {
				console.error('Error starting stream:', error);
			}
		}
	};

	// Remove a stream
	const handleRemoveStream = (id: string) => {
		setStreams(streams.filter((stream) => stream.id !== id));
	};

	// Toggle expanded state of a stream
	const toggleExpandStream = (id: string) => {
		setStreams(
			streams.map((stream) =>
				stream.id === id
					? { ...stream, isExpanded: !stream.isExpanded }
					: { ...stream, isExpanded: false }
			)
		);
	};

	// Calculate grid columns based on number of streams and expanded state
	const getGridClass = () => {
		const expandedStream = streams.find((s) => s.isExpanded);
		if (expandedStream) return 'grid-cols-1';

		if (streams.length === 0) return 'grid-cols-1';
		if (streams.length === 1) return 'grid-cols-1';
		if (streams.length === 2) return 'grid-cols-1 md:grid-cols-2';
		if (streams.length === 3 || streams.length === 4)
			return 'grid-cols-1 md:grid-cols-2';
		return 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
	};

	// Filter streams for display (when a stream is expanded, only show that one)
	const displayStreams = () => {
		const expandedStream = streams.find((s) => s.isExpanded);
		return expandedStream ? [expandedStream] : streams;
	};

	return (
		<div className="flex flex-col min-h-screen">
			<header className="px-4 lg:px-6 h-16 flex items-center border-b">
				<Link href="/" className="flex items-center justify-center">
					<Eye className="h-6 w-6 mr-2" />
					<span className="font-bold text-xl">StreamVision</span>
				</Link>
				<div className="ml-auto flex items-center gap-4">
					{isMobile && streams.length > 0 && (
						<Button
							variant="outline"
							size="sm"
							onClick={() => setShowAddForm(!showAddForm)}
							className="gap-1"
						>
							{showAddForm ? (
								'Hide Form'
							) : (
								<>
									<Plus className="h-4 w-4" /> Add Stream
								</>
							)}
						</Button>
					)}
					<Link
						href="/"
						className="flex items-center text-sm font-medium hover:underline underline-offset-4"
					>
						<ArrowLeft className="h-4 w-4 mr-1" />
						Back to Home
					</Link>
					<ThemeToggle />
				</div>
			</header>

			<main className="flex-1 flex flex-col md:flex-row p-4 md:p-6 gap-6">
				{/* Add Stream Form */}
				{(showAddForm || streams.length === 0) && (
					<Card className="w-full md:w-96 shrink-0">
						<CardHeader>
							<CardTitle>Add Stream</CardTitle>
							<CardDescription>Enter RTSP stream details below</CardDescription>
						</CardHeader>
						<form onSubmit={handleAddStream}>
							<CardContent className="space-y-4">
								<div className="space-y-2">
									<Label htmlFor="url">RTSP URL</Label>
									<Input
										id="url"
										placeholder="rtsp://your-camera-ip:port/stream"
										value={newStream.url}
										onChange={(e) =>
											setNewStream({ ...newStream, url: e.target.value })
										}
										required
									/>
								</div>
								<div className="space-y-2">
									<Label htmlFor="username">Username (optional)</Label>
									<Input
										id="username"
										value={newStream.username}
										onChange={(e) =>
											setNewStream({ ...newStream, username: e.target.value })
										}
									/>
								</div>
								<div className="space-y-2">
									<Label htmlFor="password">Password (optional)</Label>
									<Input
										id="password"
										type="password"
										value={newStream.password}
										onChange={(e) =>
											setNewStream({ ...newStream, password: e.target.value })
										}
									/>
								</div>
							</CardContent>
							<CardFooter>
								<Button type="submit" className="w-full gap-2">
									<Plus className="h-4 w-4" />
									Add Stream
								</Button>
							</CardFooter>
						</form>
					</Card>
				)}

				{/* Streams Display */}
				<div className="flex-1">
					{streams.length > 0 ? (
						<div className="space-y-4">
							<div className="flex items-center justify-between">
								<h2 className="text-xl font-bold">
									Active Streams ({streams.length})
								</h2>
								{!isMobile && streams.length > 0 && (
									<Button
										variant="outline"
										size="sm"
										onClick={() => setShowAddForm(!showAddForm)}
										className="gap-1"
									>
										{showAddForm ? (
											'Hide Add Form'
										) : (
											<>
												<Plus className="h-4 w-4" /> Add Stream
											</>
										)}
									</Button>
								)}
							</div>

							<div className={`grid ${getGridClass()} gap-4 auto-rows-fr`}>
								{displayStreams().map((stream) => (
									<div
										key={stream.id}
										className={`relative rounded-lg border overflow-hidden ${
											stream.isExpanded
												? 'col-span-full row-span-full h-[60vh]'
												: 'h-[30vh] md:h-[40vh]'
										}`}
									>
										<video
											ref={stream.videoRef}
											className="w-full h-full object-cover"
											controls
											playsInline
										/>
										<div className="absolute top-2 right-2 flex gap-1">
											<Button
												variant="secondary"
												size="icon"
												className="h-8 w-8"
												onClick={() => toggleExpandStream(stream.id)}
											>
												{stream.isExpanded ? (
													<Minimize className="h-4 w-4" />
												) : (
													<Maximize className="h-4 w-4" />
												)}
											</Button>
											<Button
												variant="destructive"
												size="icon"
												className="h-8 w-8"
												onClick={() => handleRemoveStream(stream.id)}
											>
												<X className="h-4 w-4" />
											</Button>
										</div>
									</div>
								))}
							</div>
						</div>
					) : (
						<div className="h-full flex items-center justify-center">
							<div className="text-center space-y-4">
								<div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
									<Eye className="h-6 w-6 text-primary" />
								</div>
								<div className="space-y-2">
									<h3 className="text-lg font-medium">No Active Streams</h3>
									<p className="text-sm text-muted-foreground">
										Add your first RTSP stream to get started
									</p>
								</div>
							</div>
						</div>
					)}
				</div>
			</main>

			{/* Stream List on Mobile (when form is hidden) */}
			{isMobile && !showAddForm && streams.length > 0 && (
				<div className="border-t p-4">
					<ScrollArea className="h-32">
						<div className="space-y-2">
							<h3 className="font-medium text-sm">
								All Streams ({streams.length})
							</h3>
							{streams.map((stream) => (
								<div
									key={stream.id}
									className="flex items-center justify-between py-2 border-b last:border-0"
								>
									<div className="truncate flex-1">
										<p className="text-sm font-medium truncate">{stream.url}</p>
										{stream.username && (
											<p className="text-xs text-muted-foreground">
												User: {stream.username}
											</p>
										)}
									</div>
									<div className="flex gap-1 ml-2">
										<Button
											variant="outline"
											size="icon"
											className="h-7 w-7"
											onClick={() => toggleExpandStream(stream.id)}
										>
											<Maximize className="h-3 w-3" />
										</Button>
										<Button
											variant="outline"
											size="icon"
											className="h-7 w-7"
											onClick={() => handleRemoveStream(stream.id)}
										>
											<X className="h-3 w-3" />
										</Button>
									</div>
								</div>
							))}
						</div>
					</ScrollArea>
				</div>
			)}

			<footer className="flex flex-col gap-2 sm:flex-row py-6 w-full shrink-0 items-center px-4 md:px-6 border-t">
				<p className="text-xs text-muted-foreground">
					&copy; {new Date().getFullYear()} StreamVision. All rights reserved.
				</p>
			</footer>
		</div>
	);
}
